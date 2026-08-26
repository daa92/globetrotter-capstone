"""
app/routers/itineraries.py

Trip-planning CRUD, scoped to the authenticated user, plus route
computation: given an ordered list of destinations (and an optional
starting point — the user's location, or any city they pick), returns
the total distance/duration and, when OPENROUTESERVICE_API_KEY is
configured, the actual road-route geometry for drawing on a map. Falls
back to straight-line (haversine) distance with no key configured, so
the feature still works — just without a real road-following line —
with zero external setup.
"""
import math
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app import geo_service, storage, transport_companies
from app.dependencies import get_current_user
from app.schemas import Itinerary, ItineraryCreate, RouteRequest, RouteResponse, RouteStop, TransportSuggestion

router = APIRouter(prefix="/itineraries", tags=["itineraries"])


@router.post("", response_model=Itinerary, status_code=status.HTTP_201_CREATED)
def create_itinerary(payload: ItineraryCreate, user: dict = Depends(get_current_user)):
    itinerary = {
        "id": str(uuid.uuid4()),
        "username": user["username"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        **payload.model_dump(mode="json"),
    }
    storage.append(storage.ITINERARIES_FILE, itinerary)
    return Itinerary(**itinerary)


@router.get("", response_model=list[Itinerary])
def list_my_itineraries(user: dict = Depends(get_current_user)):
    itineraries = storage.read_all(storage.ITINERARIES_FILE)
    mine = [it for it in itineraries if it["username"] == user["username"]]
    return [Itinerary(**it) for it in mine]


@router.delete("/{itinerary_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_itinerary(itinerary_id: str, user: dict = Depends(get_current_user)):
    itineraries = storage.read_all(storage.ITINERARIES_FILE)
    match = next((it for it in itineraries if it["id"] == itinerary_id), None)
    if not match:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Itinerary not found")
    if match["username"] != user["username"]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your itinerary")
    storage.delete_one(storage.ITINERARIES_FILE, "id", itinerary_id)
    return None


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


@router.post("/route-preview", response_model=RouteResponse)
def preview_route(payload: RouteRequest, user: dict = Depends(get_current_user)):
    """Works both for a trip you're still planning (not saved yet — the
    frontend calls this live as you pick destinations) and for viewing a
    saved trip's route (frontend just passes that itinerary's
    destination list). Not itinerary-ID-scoped on purpose, so it works
    either way without two near-duplicate endpoints."""
    destinations = storage.read_all(storage.DESTINATIONS_FILE)
    by_id = {d["id"]: d for d in destinations}

    missing = [did for did in payload.destination_ids if did not in by_id]
    if missing:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown destination id(s): {', '.join(missing)}")

    stops: list[RouteStop] = []
    if payload.start_lat is not None and payload.start_lng is not None:
        stops.append(RouteStop(name=payload.start_label or "Start", latitude=payload.start_lat, longitude=payload.start_lng))
    for did in payload.destination_ids:
        d = by_id[did]
        stops.append(RouteStop(name=d["name"], latitude=d["latitude"], longitude=d["longitude"]))

    if len(stops) < 2:
        # A single destination with no start point — nothing to route,
        # but still return a valid, zero-distance response rather than
        # erroring, since "just show me this one place" is reasonable.
        return RouteResponse(stops=stops, total_distance_km=0.0, method="straight_line", transport_suggestions=[])

    waypoints = [(s.latitude, s.longitude) for s in stops]
    geometry: list[list[float]] = []
    duration_minutes = None
    method = "straight_line"

    try:
        route, _ = geo_service.get_multi_route(waypoints)
        total_km = route["distance_km"]
        duration_minutes = route["duration_minutes"]
        geometry = route["geometry"]
        method = "driving"
    except Exception:  # noqa: BLE001 — ORS unset/unreachable/rate-limited: fall back, don't break the page
        total_km = sum(
            _haversine_km(waypoints[i][0], waypoints[i][1], waypoints[i + 1][0], waypoints[i + 1][1])
            for i in range(len(waypoints) - 1)
        )

    suggestions = [TransportSuggestion(**c) for c in transport_companies.suggest_for_distance(total_km)]

    return RouteResponse(
        stops=stops,
        total_distance_km=round(total_km, 2),
        total_duration_minutes=duration_minutes,
        geometry=geometry,
        method=method,
        transport_suggestions=suggestions,
    )
