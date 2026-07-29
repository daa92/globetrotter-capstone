"""
app/__init__.py

FastAPI application factory. Kept small on purpose: this file's only job
is wiring — middleware, routers, background tasks, and the health check.
Business logic always lives in routers/, never here.
"""
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.cleanup import run_cleanup_loop
from app.config import settings
from app.routers import auth, destinations, feedback, itineraries, places, recommendations, users


@asynccontextmanager
async def lifespan(app: FastAPI):
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
    app.include_router(destinations.router)
    app.include_router(recommendations.router)
    app.include_router(itineraries.router)
    app.include_router(places.router)
    app.include_router(feedback.router)

    @app.get("/health", tags=["meta"])
    def health():
        """Liveness/readiness probe. Kubernetes will use this from Phase 3 onward."""
        return {"status": "ok", "env": settings.ENV}

    return app
