"""
app/__init__.py

FastAPI application factory. Kept small on purpose: this file's only job
is wiring — middleware, routers, and the health check. Business logic
always lives in routers/, never here.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth, destinations, feedback, itineraries, places, recommendations, users


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        description="GT (GlobeTrotter) — discover and plan trips across Cameroon.",
        version="0.1.0-phase1",
        docs_url="/docs",
        redoc_url="/redoc",
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
