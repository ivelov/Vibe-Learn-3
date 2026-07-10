"""Health check endpoint for Docker / deployment probes."""

from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/health")
async def health(request: Request) -> dict:
    """Report liveness plus which optional subsystems are wired up."""
    state = request.app.state
    return {
        "status": "ok",
        "db_available": bool(getattr(state, "db_available", False)),
        "llm_available": bool(getattr(state, "llm_available", False)),
    }
