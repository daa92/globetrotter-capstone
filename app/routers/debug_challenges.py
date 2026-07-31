"""
app/routers/debug_challenges.py

Endpoints that exist for exactly one purpose: letting testing/challenges/
scripts *prove* the Phase 1 monolith challenges from the capstone slides,
rather than just asserting them in a report.

CRITICAL: this router is only mounted if settings.SIMULATION_MODE is True
(see app/__init__.py) — production deployments must never set that flag,
and .env.example ships with it false. This is the one place in the whole
app deliberately designed to misbehave on command.
"""
import time

from fastapi import APIRouter, Query

router = APIRouter(prefix="/debug/challenges", tags=["debug (simulation only)"])


@router.get("/blocking-call")
def blocking_call(seconds: float = Query(default=3.0, ge=0, le=30)):
    """A deliberately SYNCHRONOUS, BLOCKING sleep (time.sleep, not
    await asyncio.sleep). FastAPI runs sync `def` routes in a limited
    thread pool — enough concurrent calls to this endpoint exhaust that
    pool and start stalling requests to completely unrelated endpoints
    too, because this monolith shares one process/one thread pool across
    every "service." That's the whole point of this endpoint existing.
    """
    time.sleep(seconds)
    return {"slept_seconds": seconds}


@router.get("/crash")
def crash():
    """Deliberately raises an unhandled exception, to observe exactly
    what does and doesn't survive it (see testing/challenges/README.md
    for what this does and doesn't prove — FastAPI catches this per-request,
    which is itself a useful, honest finding, not a false claim)."""
    return 1 / 0  # noqa: intentional
