"""
app/__init__.py

FastAPI application factory. Kept small on purpose: this file's only job
is wiring — middleware, routers, background tasks, and the health check.
Business logic always lives in routers/, never here.
"""
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.cleanup import run_cleanup_loop
from app.config import settings
from app.db import init_db
from app.routers import auth, admin_users, admin_overview, destinations, earnings, feedback, geo, itineraries, notifications, places, recommendations, users

logger = logging.getLogger("gt.app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()  # idempotent — creates the `store` table if it doesn't exist yet
    # Background task: purges unverified accounts older than
    # UNVERIFIED_ACCOUNT_TTL_MINUTES, every VERIFICATION_CLEANUP_INTERVAL_SECONDS.
    cleanup_task = asyncio.create_task(run_cleanup_loop())
    yield
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        description="GT (GlobeTrotter) — discover and plan trips across Cameroon.",
        version="0.1.0-phase1",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,  # required so the refresh cookie is sent cross-origin
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(admin_users.router)
    app.include_router(admin_overview.router)
    app.include_router(destinations.router)
    app.include_router(recommendations.router)
    app.include_router(itineraries.router)
    app.include_router(places.router)
    app.include_router(feedback.router)
    app.include_router(earnings.router)
    app.include_router(notifications.router)
    app.include_router(geo.router)

    if settings.SIMULATION_MODE:
        from app.routers import debug_challenges
        app.include_router(debug_challenges.router)
        logger.warning(
            "SIMULATION_MODE is ON — /debug/challenges/* endpoints are live. "
            "These exist ONLY to prove capstone failure-mode challenges on "
            "demand. NEVER set SIMULATION_MODE=true in production."
        )

    @app.get("/health", tags=["meta"])
    def health():
        """Liveness/readiness probe. Kubernetes will use this from Phase 3 onward."""
        return {"status": "ok", "env": settings.ENV}

    return app
