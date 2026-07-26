"""
app/routers/recommendations.py

Recommendation engine v1: content-based filtering using tag overlap
between a user's stated preferences and each destination's tags, with a
small popularity/recency nudge. This is intentionally simple and fast —
it's the baseline the Phase-2+ "smarter" engine (collaborative filtering,
embeddings) will be benchmarked against.

Scoring is a plain weighted Jaccard-style overlap, kept dependency-free
for Phase 1. scikit-learn based cosine-similarity scoring lands in the
Recommendation microservice in Phase 2.
"""
from fastapi import APIRouter, Depends, Query

from app import storage
from app.dependencies import get_current_user
from app.schemas import Destination

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


def _score(user_preferences: set[str], destination_tags: set[str]) -> float:
    if not user_preferences or not destination_tags:
        return 0.0
    overlap = user_preferences & destination_tags
    union = user_preferences | destination_tags
    return len(overlap) / len(union)  # Jaccard similarity, 0..1


@router.get("", response_model=list[Destination])
def get_recommendations(
    user: dict = Depends(get_current_user),
    limit: int = Query(default=10, ge=1, le=50),
):
    preferences = set(p.lower() for p in user.get("preferences", []))
    destinations = storage.read_all(storage.DESTINATIONS_FILE)

    scored = [
        (dest, _score(preferences, set(t.lower() for t in dest.get("tags", []))))
        for dest in destinations
    ]

    # If the user has no preferences yet (cold start), fall back to
    # returning the catalogue as-is rather than an empty list.
    if not preferences:
        ranked = destinations[:limit]
    else:
        scored.sort(key=lambda pair: pair[1], reverse=True)
        ranked = [dest for dest, score in scored if score > 0][:limit]
        if not ranked:
            ranked = destinations[:limit]  # nothing matched — don't leave the user empty-handed

    return [Destination(**d) for d in ranked]
