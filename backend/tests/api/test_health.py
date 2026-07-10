"""Tests for the health router."""

from __future__ import annotations

from tests.api.conftest import client_for, make_app


def test_health_reports_subsystems():
    app = make_app(db_available=True, llm_available=False)
    resp = client_for(app).get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "db_available": True, "llm_available": False}


def test_health_defaults_false_when_unset():
    app = make_app()
    resp = client_for(app).get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["db_available"] is False
    assert body["llm_available"] is False
