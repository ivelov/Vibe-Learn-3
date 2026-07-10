#!/usr/bin/env bash
# FinAlly — start script (macOS / Linux)
# Idempotent: safe to run repeatedly. Rebuilds the image, replaces any running
# container, and mounts a named volume so the SQLite database persists.
set -euo pipefail

# Always operate from the project root regardless of where this is invoked.
cd "$(dirname "$0")/.."

IMAGE="finally:latest"
CONTAINER="finally"

if [ ! -f .env ]; then
  if [ -f .env.example ]; then
    echo "No .env found — creating one from .env.example."
    echo "  -> Edit .env and set OPENROUTER_KEY before using the AI chat."
    cp .env.example .env
  else
    echo "Error: no .env or .env.example in $(pwd). Aborting." >&2
    exit 1
  fi
fi

echo "Building FinAlly Docker image ($IMAGE)..."
docker build -t "$IMAGE" .

echo "Removing any existing '$CONTAINER' container..."
docker rm -f "$CONTAINER" >/dev/null 2>&1 || true

echo "Starting FinAlly..."
docker run -d \
  --name "$CONTAINER" \
  -v finally-data:/app/db \
  -p 8000:8000 \
  --env-file .env \
  --restart unless-stopped \
  "$IMAGE"

echo "Waiting for FinAlly to become healthy..."
for _ in $(seq 1 15); do
  if curl -sf http://localhost:8000/api/health >/dev/null 2>&1; then
    echo "FinAlly is running at http://localhost:8000"
    echo "Open http://localhost:8000 in your browser."
    exit 0
  fi
  sleep 1
done

echo "Warning: health check did not pass yet. The container may still be starting." >&2
echo "Check logs with: docker logs $CONTAINER" >&2
