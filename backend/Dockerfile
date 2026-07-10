# FinAlly — AI Trading Workstation
# Single-stage: Python serves API + pre-built static frontend.
#
# Railway uses this file's directory as the Docker build context (backend/).
# The frontend static export lives in frontend_out/ (a copy of frontend/out/).

FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir "poetry==2.2.1"

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_VIRTUALENVS_IN_PROJECT=false

COPY pyproject.toml poetry.lock* ./
RUN poetry install --no-root

COPY app ./app

# Pre-built Next.js static export (frontend/out/ copied here for Railway).
COPY frontend_out ./static

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Railway mounts a persistent volume at /app/db (configured in Railway dashboard).
RUN mkdir -p /app/db

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
