"""
app/routers/destinations.py

Public search over the Cameroon destination catalogue. Phase 1 filtering
is straightforward (tag/region/cost/text), but it's written as composable
predicate filters so Phase 2+ can extend it (radius search, popularity
ranking, full-text scoring) without a rewrite.
"""
from fastapi import APIRouter, Query

from app import storage
from app.schemas import Destination

router = APIRouter(prefix="/destinations", tags=["destinations"])


@router.get("", response_model=list[Destination])
def search_destinations(
    q: str | None = Query(default=None, description="Free-text search over name/description"),
    tag: str | None = Query(default=None, description="Filter by a single tag, e.g. 'beach'"),
    region: str | None = Query(default=None),
    max_cost: int | None = Query(default=None, ge=0),
):
    destinations = storage.read_all(storage.DESTINATIONS_FILE)

    def matches(d: dict) -> bool:
        if q and q.lower() not in d["name"].lower() and q.lower() not in d["description"].lower():
            return False
        if tag and tag.lower() not in [t.lower() for t in d.get("tags", [])]:
            return False
        if region and region.lower() != d.get("region", "").lower():
            return False
        if max_cost is not None and d.get("avg_cost_fcfa") is not None and d["avg_cost_fcfa"] > max_cost:
            return False
        return True

    return [Destination(**d) for d in destinations if matches(d)]


@router.get("/{destination_id}", response_model=Destination)
def get_destination(destination_id: str):
    destinations = storage.read_all(storage.DESTINATIONS_FILE)
    match = next((d for d in destinations if d["id"] == destination_id), None)
    if not match:
        from fastapi import HTTPException, status
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Destination not found")
    return Destination(**match)
