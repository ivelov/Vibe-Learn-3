"""The FinAlly chat engine — wraps LiteLLM/OpenRouter (Cerebras) with a mock mode.

The public entry point is :meth:`ChatEngine.get_response`, which is guaranteed
never to raise: any connection or parsing failure is caught and surfaced as a
``ChatResponse`` whose ``message`` explains the problem to the user.
"""

from __future__ import annotations

import json
import logging
import re

from .prompts import build_system_prompt, build_user_message
from .schema import ChatResponse, TradeAction, WatchlistChange

logger = logging.getLogger(__name__)

# Cerebras via OpenRouter, per the cerebras-inference skill.
MODEL = "openrouter/openai/gpt-oss-120b"
EXTRA_BODY = {"provider": {"order": ["cerebras"]}}

# Rotating canned responses used by mock mode when no trade/watchlist intent is
# detected in the user's message. Deterministic given call order.
MOCK_RESPONSES: list[dict] = [
    {
        "message": (
            "Based on your portfolio, you have a healthy cash position. Your "
            "holdings look reasonable — let me know if you'd like to make any "
            "trades or rebalance."
        ),
        "trades": [],
        "watchlist_changes": [],
    },
    {
        "message": (
            "I've analyzed your portfolio. Your watchlist is well-diversified "
            "across tech and finance. Would you like to build or trim any "
            "positions?"
        ),
        "trades": [],
        "watchlist_changes": [],
    },
    {
        "message": (
            "Markets are moving. TSLA and NVDA have been the most volatile names "
            "on your watchlist lately — worth watching closely."
        ),
        "trades": [],
        "watchlist_changes": [],
    },
]

# Matches phrases like "buy 10 AAPL", "sell 2.5 shares of TSLA".
_TRADE_RE = re.compile(
    r"\b(buy|sell)\b\s+(\d+(?:\.\d+)?)\s+(?:shares?\s+of\s+)?([A-Za-z]{1,5})\b",
    re.IGNORECASE,
)
# Matches phrases like "add PYPL", "remove NFLX from watchlist".
_WATCHLIST_RE = re.compile(
    r"\b(add|remove)\b\s+([A-Za-z]{1,5})\b",
    re.IGNORECASE,
)


class ChatEngine:
    """Generates assistant chat responses, optionally against a live LLM.

    Args:
        api_key: OpenRouter API key (from ``OPENROUTER_KEY``). Passed explicitly
            to LiteLLM, which otherwise reads ``OPENROUTER_API_KEY``.
        mock: When True, return deterministic responses without any network call.
    """

    def __init__(self, api_key: str, mock: bool = False):
        self.api_key = api_key
        self.mock = mock
        self._mock_index = 0

    def get_response(
        self,
        portfolio_context: dict,
        watchlist_context: list[dict],
        conversation_history: list[dict],
        user_message: str,
    ) -> ChatResponse:
        """Return a :class:`ChatResponse` for the user's message.

        Never raises: on any failure a ``ChatResponse`` carrying an explanatory
        message is returned so the API layer can always respond.
        """
        if self.mock:
            return self._get_mock_response(user_message)

        try:
            return self._call_llm(
                portfolio_context,
                watchlist_context,
                conversation_history,
                user_message,
            )
        except Exception:  # noqa: BLE001 - boundary: must never propagate
            logger.exception("Unexpected error generating chat response")
            return ChatResponse(
                message=(
                    "I ran into an unexpected problem while processing that. "
                    "Please try again in a moment."
                )
            )

    # ------------------------------------------------------------------ mock

    def _get_mock_response(self, user_message: str) -> ChatResponse:
        """Deterministic mock response.

        Understands simple "buy/sell N TICKER" and "add/remove TICKER" phrasing
        so E2E tests (which run with ``LLM_MOCK=true``) can exercise inline trade
        execution and watchlist changes. Otherwise rotates canned analysis text.
        """
        text = user_message or ""

        trades = [
            TradeAction(side=side.lower(), quantity=float(qty), ticker=ticker.upper())
            for side, qty, ticker in _TRADE_RE.findall(text)
        ]
        watchlist_changes = [
            WatchlistChange(action=action.lower(), ticker=ticker.upper())
            for action, ticker in _WATCHLIST_RE.findall(text)
        ]

        if trades or watchlist_changes:
            parts: list[str] = []
            for t in trades:
                parts.append(f"{t.side} {t.quantity:g} {t.ticker}")
            for w in watchlist_changes:
                verb = "Added" if w.action == "add" else "Removed"
                parts.append(f"{verb.lower()} {w.ticker} on the watchlist")
            summary = "; ".join(parts)
            return ChatResponse(
                message=f"Done — I processed the following: {summary}.",
                trades=trades,
                watchlist_changes=watchlist_changes,
            )

        resp = MOCK_RESPONSES[self._mock_index % len(MOCK_RESPONSES)]
        self._mock_index += 1
        return ChatResponse.model_validate(resp)

    # ------------------------------------------------------------------- live

    def _call_llm(
        self,
        portfolio_context: dict,
        watchlist_context: list[dict],
        conversation_history: list[dict],
        user_message: str,
    ) -> ChatResponse:
        """Call the LLM via LiteLLM with structured output and parse the result."""
        from litellm import completion  # local import: keeps mock/tests litellm-free

        messages = [
            {"role": "system", "content": build_system_prompt()},
            {
                "role": "user",
                "content": build_user_message(
                    portfolio_context,
                    watchlist_context,
                    conversation_history,
                    user_message,
                ),
            },
        ]

        try:
            response = completion(
                model=MODEL,
                messages=messages,
                response_format=ChatResponse,
                reasoning_effort="low",
                extra_body=EXTRA_BODY,
                api_key=self.api_key,
                drop_params=True,
            )
        except Exception:
            logger.exception("LLM API call failed")
            return ChatResponse(
                message=(
                    "I'm having trouble reaching my AI service right now. "
                    "Please try again shortly."
                )
            )

        content = response.choices[0].message.content
        return self._parse_response(content)

    def _parse_response(self, content: str | None) -> ChatResponse:
        """Parse raw model content into a ChatResponse, degrading gracefully."""
        if not content or not content.strip():
            logger.error("LLM returned empty content")
            return ChatResponse(
                message="I received an empty response. Please try asking again."
            )

        # Happy path: content is exactly the structured JSON.
        try:
            return ChatResponse.model_validate_json(content)
        except Exception:
            logger.warning("Direct JSON validation failed; attempting extraction")

        # Fallback: extract the first {...} block and validate that.
        extracted = _extract_json_object(content)
        if extracted is not None:
            try:
                return ChatResponse.model_validate(extracted)
            except Exception:
                # If at least a message is present, use it verbatim.
                message = extracted.get("message")
                if isinstance(message, str) and message.strip():
                    logger.warning("Recovered message field from malformed response")
                    return ChatResponse(message=message)

        logger.error("Failed to parse LLM response as ChatResponse: %r", content)
        return ChatResponse(
            message=(
                "I had trouble formatting my response. Here's what I was going "
                "to say:\n\n" + content.strip()
            )
        )


def _extract_json_object(text: str) -> dict | None:
    """Best-effort extraction of the first top-level JSON object from text."""
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    candidate = text[start : end + 1]
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None
