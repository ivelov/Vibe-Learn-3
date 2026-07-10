"""LLM integration for FinAlly — chat engine, schemas, and prompt builders."""

from .engine import ChatEngine
from .exceptions import LLMConnectionError, LLMError, LLMParseError
from .prompts import build_system_prompt, build_user_message
from .schema import ChatResponse, TradeAction, WatchlistChange

__all__ = [
    "ChatEngine",
    "ChatResponse",
    "TradeAction",
    "WatchlistChange",
    "build_system_prompt",
    "build_user_message",
    "LLMError",
    "LLMParseError",
    "LLMConnectionError",
]
