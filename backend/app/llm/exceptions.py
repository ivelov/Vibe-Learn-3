"""Exceptions for the LLM integration layer.

The public :class:`~app.llm.engine.ChatEngine` API never raises these — it
catches errors internally and returns a graceful ``ChatResponse``. They exist so
internal helpers can signal specific failure modes and so callers/tests can
assert on them if they choose to use lower-level helpers directly.
"""

from __future__ import annotations


class LLMError(Exception):
    """Base exception for LLM errors."""


class LLMParseError(LLMError):
    """Failed to parse an LLM response as a valid ChatResponse."""


class LLMConnectionError(LLMError):
    """Failed to connect to or complete a request against the LLM API."""
