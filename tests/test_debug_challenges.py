"""
tests/test_debug_challenges.py

The one thing that matters most about app/routers/debug_challenges.py is
that it's genuinely inaccessible unless SIMULATION_MODE is explicitly on
— this is tested directly rather than assumed.
"""
import pytest
from fastapi.testclient import TestClient

from app import create_app


def test_debug_endpoints_absent_when_simulation_mode_off(monkeypatch):
    monkeypatch.setattr("app.config.settings.SIMULATION_MODE", False)
    app = create_app()
    with TestClient(app) as client:
        resp = client.get("/debug/challenges/crash")
        assert resp.status_code == 404  # route doesn't exist at all, not just forbidden


def test_debug_endpoints_present_when_simulation_mode_on(monkeypatch):
    monkeypatch.setattr("app.config.settings.SIMULATION_MODE", True)
    app = create_app()
    with TestClient(app) as client:
        resp = client.get("/debug/challenges/blocking-call", params={"seconds": 0})
        assert resp.status_code == 200
        assert resp.json()["slept_seconds"] == 0


def test_crash_endpoint_returns_500_not_a_dead_process(monkeypatch):
    """FastAPI catches this per-request — the process itself survives.
    This is an honest, useful finding for the report: request-level
    exceptions ARE isolated by the framework; what genuinely ISN'T
    isolated is a blocking synchronous call starving the shared thread
    pool (see testing/challenges/ for that proof, which needs a real
    running server with real concurrency, not TestClient)."""
    monkeypatch.setattr("app.config.settings.SIMULATION_MODE", True)
    app = create_app()
    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.get("/debug/challenges/crash")
        assert resp.status_code == 500
        # The app is still alive and other endpoints still work fine.
        health = client.get("/health")
        assert health.status_code == 200
