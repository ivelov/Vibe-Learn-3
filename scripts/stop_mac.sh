#!/usr/bin/env bash
# FinAlly — stop script (macOS / Linux)
# Stops and removes the container. The named volume (finally-data) is kept so
# the portfolio, watchlist, and trade history survive across restarts.
set -euo pipefail

CONTAINER="finally"

echo "Stopping FinAlly container..."
docker stop "$CONTAINER" >/dev/null 2>&1 || true
docker rm "$CONTAINER" >/dev/null 2>&1 || true

echo "FinAlly stopped. Data persists in the 'finally-data' volume."
echo "To remove all saved data: docker volume rm finally-data"
