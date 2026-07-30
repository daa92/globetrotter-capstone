"""
app/routers/geo.py

Public, unauthenticated endpoints wrapping the free map/geo stack
(app/geo.py). Every response includes `cached: true/false` so it's
obvious at a glance whether a request actually hit the live API or was
served from our own cache — useful for debugging and for demonstrating
we're respecting these services' rate limits.
"""
from fastapi import APIRouter, HTTPException, Query, status

from app import geo_service as geo
from app.config import settings

router = APIRouter(prefix="/geo", tags=["geo"])


@router.get("/search")
def search(q: str = Query(min_length=2, description="Place name to search for, e.g. 'Mont Cameroun'")):
    try:
        results, was_cached = geo.search_places(q)
    except Exception as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, f"Could not search places: {exc}")
    return {"query": q, "cached": was_cached, "results": results}


@router.get("/route")
def route(
    from_lat: float,
    from_lng: float,
    to_lat: float,
    to_lng: float,
    profile: str = Query(default="foot-walking", pattern="^(foot-walking|driving-car|cycling-regular)$"),
):
    if not settings.OPENROUTESERVICE_API_KEY:
        raise HTTPException(
            status.HTTP_501_NOT_IMPLEMENTED,
            "Route planning is not configured on this server (missing OPENROUTESERVICE_API_KEY)",
        )
    try:
        result, was_cached = geo.get_route(from_lat, from_lng, to_lat, to_lng, profile)
    except Exception as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, f"Could not compute route: {exc}")
    return {**result, "cached": was_cached}


@router.get("/poi")
def poi(
    amenity: str = Query(description="e.g. restaurant, hospital, fuel, bank, pharmacy"),
    lat: float = Query(...),
    lon: float = Query(...),
    radius_m: int = Query(default=5000, le=20000),
):
    try:
        results, was_cached = geo.search_pois(amenity, lat, lon, radius_m)
    except Exception as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, f"Could not search points of interest: {exc}")
    return {"amenity": amenity, "cached": was_cached, "results": results}
