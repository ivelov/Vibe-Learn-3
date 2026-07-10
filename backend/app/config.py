"""Application configuration derived from environment variables.

Read once at import time. The backend reads ``.env`` from the project root
(loaded by the process manager / Docker ``--env-file``); we only consult
``os.environ`` here so there is a single source of truth.
"""

from __future__ import annotations

import os
from pathlib import Path

# --- Database ---------------------------------------------------------------
# Matches the DB layer's default (backend/db/finally.db) and honors the same
# FINALLY_DB_PATH override so tests and alternate deployments stay consistent.
_DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "db" / "finally.db"
DB_PATH = Path(os.getenv("FINALLY_DB_PATH", str(_DEFAULT_DB_PATH)))

# --- LLM --------------------------------------------------------------------
# The project .env uses OPENROUTER_KEY (see PLAN.md section 9 / project root).
OPENROUTER_API_KEY = os.getenv("OPENROUTER_KEY", "") or os.getenv("OPENROUTER_API_KEY", "")

# When true, the LLM layer returns deterministic mock responses (E2E / CI).
LLM_MOCK = os.getenv("LLM_MOCK", "false").lower() == "true"

# --- Market data ------------------------------------------------------------
# If set and non-empty, the market factory uses the Massive API; else simulator.
MASSIVE_API_KEY = os.getenv("MASSIVE_API_KEY", "")

# --- Domain constants -------------------------------------------------------
DEFAULT_USER_ID = "default"

DEFAULT_TICKERS = [
    "AAPL", "GOOGL", "MSFT", "AMZN", "TSLA",
    "NVDA", "META", "JPM", "V", "NFLX",
]

# How often the background task records a portfolio value snapshot (seconds).
SNAPSHOT_INTERVAL_SECONDS = 30.0
