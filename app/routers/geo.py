"""
app/routers/geo.py

Public, unauthenticated endpoints wrapping the free map/geo stack
(app/geo_service.py). Every response includes `cached: true/false` so it's
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


@router.get("/poi-categories")
def poi_categories():
    """The full list of supported POI categories — the frontend builds its
    filter chips from this instead of hardcoding a list that could drift
    out of sync with what the backend actually supports."""
    return {"categories": sorted(geo.CATEGORY_TAGS.keys())}


@router.get("/poi")
def poi(
    category: str = Query(description="e.g. restaurant, fast_food, airport, hotel, hospital, bank, fuel, supermarket"),
    lat: float = Query(...),
    lon: float = Query(...),
    radius_m: int = Query(default=5000, le=20000),
):
    if category not in geo.CATEGORY_TAGS:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Unknown category '{category}'. Valid categories: {', '.join(sorted(geo.CATEGORY_TAGS))}",
        )
    try:
        results, was_cached = geo.search_pois(category, lat, lon, radius_m)
    except Exception as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, f"Could not search points of interest: {exc}")
    return {"category": category, "cached": was_cached, "results": results}


@router.get("/place-summary")
def place_summary(
    name: str = Query(min_length=2, description="Place name to look up on Wikipedia"),
    lang: str = Query(default="en", pattern="^(en|fr)$"),
):
    """Best-effort description + photo for a place, via Wikipedia — used
    for live/OSM search results, which have no curated description of
    their own. Returns found: false (not an error) if nothing matches,
    since 'no Wikipedia article' is a completely normal outcome for most
    small local places."""
    try:
        summary, was_cached = geo.get_place_summary(name, lang)
    except Exception as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, f"Could not look up '{name}': {exc}")
    if summary is None:
        return {"found": False, "cached": was_cached}
    return {"found": True, "cached": was_cached, **summary}
