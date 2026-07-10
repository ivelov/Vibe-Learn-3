# FinAlly — AI Trading Workstation
# Multi-stage build: Node builds the static frontend, Python serves everything.

# ---------------------------------------------------------------------------
# Stage 1: build the Next.js static export (produces frontend/out)
# ---------------------------------------------------------------------------
FROM node:20-slim AS frontend-builder

WORKDIR /app/frontend

# Install deps first for better layer caching. package-lock.json may not exist
# yet during early development, so match both files loosely.
COPY frontend/package*.json ./
RUN npm install

COPY frontend/ ./
RUN npm run build

# ---------------------------------------------------------------------------
# Stage 2: FastAPI app (Python 3.12) serving API + static frontend
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS app

WORKDIR /app

# curl is used by the container healthcheck (docker-compose.test.yml) and is a
# handy debugging tool inside the running container.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Poetry 2.x is required: 1.x cannot parse this project's PEP 621 pyproject.toml.
RUN pip install --no-cache-dir "poetry==2.2.1"

# Install into the system environment (no nested venv) so uvicorn lands on PATH.
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_VIRTUALENVS_IN_PROJECT=false

# Resolve dependencies before copying source so this layer caches across code
# changes. poetry.lock is optional (glob) — commit it for reproducible builds;
# without it, poetry resolves at build time (requires a resolvable pyproject).
COPY backend/pyproject.toml backend/poetry.lock* ./

# --no-root: don't build/install the project itself (source is on PYTHONPATH).
# PEP 621 dev tooling lives in optional-dependencies (extras), which poetry
# excludes by default — so no --without/--no-dev flag is needed (and --no-dev
# was removed in Poetry 2.x).
RUN poetry install --no-root

# Application source. The DB layer, schema, and seed logic all live inside the
# app package (backend/app/db); there is no separate backend/db to copy.
COPY backend/app ./app

# Static frontend export from stage 1. FastAPI serves this at /.
COPY --from=frontend-builder /app/frontend/out ./static

# Expose the app package to imports (the project itself is not installed).
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# The SQLite database lives here at runtime (db/finally.db resolves to
# /app/db/finally.db) and is backed by a named volume for persistence.
RUN mkdir -p /app/db
VOLUME ["/app/db"]

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
