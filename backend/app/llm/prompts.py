"""System prompt and user-message construction for the FinAlly assistant."""

from __future__ import annotations


def build_system_prompt() -> str:
    """Return the system prompt that defines the FinAlly assistant's behavior."""
    return """You are FinAlly, an AI trading assistant integrated into a trading workstation.

You have access to a user's live, simulated trading portfolio. You can:
- Analyze portfolio composition, risk concentration, and P&L
- Suggest and execute trades when the user asks or agrees
- Manage the watchlist (add/remove tickers)
- Explain market movements and positions

IMPORTANT RULES:
- ALWAYS respond with valid JSON matching the provided schema.
- Be concise and data-driven in your responses.
- Execute trades automatically when the user asks — no confirmation needed (this is a simulated portfolio with fake money).
- Before proposing a trade, sanity-check it against the context: buys need sufficient cash, sells need sufficient shares. If it cannot be executed, explain why in your message instead of emitting the trade.
- Never invent stock prices or data — use only the prices provided in the context.
- Do not recommend penny stocks, pump-and-dump schemes, or highly leveraged strategies.
- The "message" field is the only text the user sees; put all explanation there. Put executable actions in "trades" and "watchlist_changes".

Respond with JSON only — no prose or markdown outside the JSON structure."""


def build_user_message(
    portfolio_context: dict,
    watchlist_context: list[dict],
    conversation_history: list[dict],
    new_message: str,
) -> str:
    """Build a rich, single user message containing all context for the LLM.

    Uses defensive ``.get()`` access so a partially-populated context never
    raises — the engine treats message construction as part of the request and
    must degrade gracefully.
    """
    lines: list[str] = []

    cash = float(portfolio_context.get("cash_balance", 0.0) or 0.0)
    total = float(portfolio_context.get("total_value", 0.0) or 0.0)
    positions = portfolio_context.get("positions") or []

    lines.append("PORTFOLIO CONTEXT:")
    lines.append(f"Cash: ${cash:,.2f}")
    lines.append(f"Total Portfolio Value: ${total:,.2f}")
    if positions:
        lines.append("Current Positions:")
        for p in positions:
            lines.append(
                f"  {p.get('ticker', '?')}: {p.get('quantity', 0)} shares "
                f"@ avg ${float(p.get('avg_cost', 0.0) or 0.0):.2f}, "
                f"current ${float(p.get('current_price', 0.0) or 0.0):.2f}, "
                f"P&L: ${float(p.get('unrealized_pnl', 0.0) or 0.0):+.2f} "
                f"({float(p.get('pnl_pct', 0.0) or 0.0):+.2f}%)"
            )
    else:
        lines.append("No open positions.")

    lines.append("")
    lines.append("WATCHLIST (with live prices):")
    if watchlist_context:
        for w in watchlist_context:
            lines.append(
                f"  {w.get('ticker', '?')}: "
                f"${float(w.get('price', 0.0) or 0.0):.2f} "
                f"({w.get('direction', 'flat')} "
                f"{abs(float(w.get('change_percent', 0.0) or 0.0)):.2f}%)"
            )
    else:
        lines.append("  (empty)")

    if conversation_history:
        lines.append("")
        lines.append("CONVERSATION HISTORY:")
        for msg in conversation_history[-10:]:
            role = "You" if msg.get("role") == "user" else "FinAlly"
            content = str(msg.get("content", ""))[:200]
            lines.append(f"{role}: {content}")

    lines.append("")
    lines.append(f"User: {new_message}")
    return "\n".join(lines)
