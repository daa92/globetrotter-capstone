"""
app/routers/destinations.py

Public search over the Cameroon destination catalogue. Phase 1 filtering
is straightforward (tag/region/cost/text), but it's written as composable
predicate filters so Phase 2+ can extend it (radius search, popularity
ranking, full-text scoring) without a rewrite.

Also: content enrichment (admin-triggered, pulls real photos/description/
rating/directions from free external APIs — see app/enrichment.py) and
first-party like/dislike voting (genuine GT-user engagement, since no
free API gives real crowd ratings for most Cameroon locations).
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app import enrichment, seeding, storage
from app.audit import log_action
from app.dependencies import get_current_user, require_permission
from app.schemas import AdminDestinationUpdate, CommentCreate, CommentOut, Destination, EnrichmentResult, VoteResponse

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


# Admin: seed the curated Cameroon starter catalogue from the dashboard,
# no shell access anywhere required — see app/seeding.py. Batched for
# the same reason enrich-all (below) is: a free-tier host's request
# timeout doesn't play well with a few dozen external-API calls in one
# HTTP request.
#
# MUST be declared before GET /{destination_id} below — otherwise
# FastAPI's first-match routing would treat "seed-status" as a
# destination_id and this route would never be reached.
@router.get("/seed-status")
def get_seed_status(admin: dict = Depends(require_permission("places"))):
    return seeding.seed_status()


@router.get("/{destination_id}", response_model=Destination)
def get_destination(destination_id: str):
    destinations = storage.read_all(storage.DESTINATIONS_FILE)
    match = next((d for d in destinations if d["id"] == destination_id), None)
    if not match:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Destination not found")
    return Destination(**match)


# ---------------------------------------------------------------------------
# Admin: direct destination editing/deletion — covers EVERY destination,
# including official seed data that was never a place submission (so
# has no PLACES_FILE record at all) and places submitted by other
# users. This is how translations get added (edit with
# description_language set), and how an admin cleans up/corrects the
# catalogue directly, without the approval-workflow concepts in
# app/routers/places.py applying at all.
# ---------------------------------------------------------------------------

def _apply_description_update(existing_record: dict, updates: dict, payload) -> dict:
    """Same behavior as places.py's version — kept as a separate copy
    rather than a shared import to keep each router's admin-edit logic
    self-contained and easy to reason about independently."""
    description_language = getattr(payload, "description_language", None)
    if "description" in updates and description_language and description_language.lower() != "en":
        translations = dict(existing_record.get("description_translations", {}))
        translations[description_language.lower()] = updates.pop("description")
        updates["description_translations"] = translations
    updates.pop("description_language", None)
    return updates


@router.patch("/{destination_id}", response_model=Destination)
def admin_edit_destination(destination_id: str, payload: AdminDestinationUpdate, admin: dict = Depends(require_permission("places"))):
    destination = _get_destination_or_404(destination_id)
    updates = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    updates = _apply_description_update(destination, updates, payload)

    if not updates:
        return Destination(**destination)

    storage.update_one(storage.DESTINATIONS_FILE, "id", destination_id, updates)

    # Keep the PLACES_FILE record in sync too, if this destination came
    # from a submission — otherwise a later place-side edit could
    # silently clobber the admin's direct edit.
    places = storage.read_all(storage.PLACES_FILE)
    if any(p["id"] == destination_id for p in places):
        storage.update_one(storage.PLACES_FILE, "id", destination_id, updates)

    was_translation = "description_translations" in updates
    log_action(
        admin["username"], "destination.edited", target=destination_id,
        details=f"added {payload.description_language} translation" if was_translation else f"fields: {', '.join(updates.keys())}",
    )
    return Destination(**_get_destination_or_404(destination_id))


@router.delete("/{destination_id}")
def admin_delete_destination(destination_id: str, admin: dict = Depends(require_permission("places"))):
    destination = _get_destination_or_404(destination_id)
    storage.delete_one(storage.DESTINATIONS_FILE, "id", destination_id)

    # If it also has a PLACES_FILE submission record, remove that too —
    # otherwise it'd still show up in the submitter's "My places" list
    # pointing at a destination that no longer exists.
    places = storage.read_all(storage.PLACES_FILE)
    if any(p["id"] == destination_id for p in places):
        storage.delete_one(storage.PLACES_FILE, "id", destination_id)

    log_action(admin["username"], "destination.deleted", target=destination["name"])
    return {"detail": f"'{destination['name']}' deleted"}


# ---------------------------------------------------------------------------
# First-party voting — any logged-in user, one vote per destination, can
# switch or retract it. This is real GT-user engagement data (see
# app/enrichment.py's docstring for why this isn't sourced externally).
# ---------------------------------------------------------------------------

def _get_destination_or_404(destination_id: str) -> dict:
    destinations = storage.read_all(storage.DESTINATIONS_FILE)
    match = next((d for d in destinations if d["id"] == destination_id), None)
    if not match:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Destination not found")
    return match


def _cast_vote(destination_id: str, username: str, vote: str) -> VoteResponse:
    destination = _get_destination_or_404(destination_id)
    votes = storage.read_all(storage.DESTINATION_VOTES_FILE)
    existing = next((v for v in votes if v["destination_id"] == destination_id and v["username"] == username), None)

    likes = destination.get("likes", 0)
    dislikes = destination.get("dislikes", 0)

    if existing and existing["vote"] == vote:
        # Voting the same way again retracts it (toggle behavior).
        storage.delete_one(storage.DESTINATION_VOTES_FILE, "id", existing["id"])
        if vote == "like":
            likes = max(0, likes - 1)
        else:
            dislikes = max(0, dislikes - 1)
        your_vote = None
    elif existing:
        # Switching from like -> dislike or vice versa.
        storage.update_one(storage.DESTINATION_VOTES_FILE, "id", existing["id"], {"vote": vote})
        if vote == "like":
            likes += 1
            dislikes = max(0, dislikes - 1)
        else:
            dislikes += 1
            likes = max(0, likes - 1)
        your_vote = vote
    else:
        storage.append(
            storage.DESTINATION_VOTES_FILE,
            {"id": str(uuid.uuid4()), "destination_id": destination_id, "username": username, "vote": vote,
             "voted_at": datetime.now(timezone.utc).isoformat()},
        )
        if vote == "like":
            likes += 1
        else:
            dislikes += 1
        your_vote = vote

    storage.update_one(storage.DESTINATIONS_FILE, "id", destination_id, {"likes": likes, "dislikes": dislikes})
    return VoteResponse(destination_id=destination_id, likes=likes, dislikes=dislikes, your_vote=your_vote)


@router.post("/{destination_id}/like", response_model=VoteResponse)
def like_destination(destination_id: str, user: dict = Depends(get_current_user)):
    return _cast_vote(destination_id, user["username"], "like")


@router.post("/{destination_id}/dislike", response_model=VoteResponse)
def dislike_destination(destination_id: str, user: dict = Depends(get_current_user)):
    return _cast_vote(destination_id, user["username"], "dislike")


@router.get("/{destination_id}/my-vote", response_model=VoteResponse)
def get_my_vote(destination_id: str, user: dict = Depends(get_current_user)):
    destination = _get_destination_or_404(destination_id)
    votes = storage.read_all(storage.DESTINATION_VOTES_FILE)
    existing = next((v for v in votes if v["destination_id"] == destination_id and v["username"] == user["username"]), None)
    return VoteResponse(
        destination_id=destination_id,
        likes=destination.get("likes", 0),
        dislikes=destination.get("dislikes", 0),
        your_vote=existing["vote"] if existing else None,
    )


# ---------------------------------------------------------------------------
# Comments — public to read, any logged-in user can post, owner or admin
# can delete.
# ---------------------------------------------------------------------------

@router.get("/{destination_id}/comments", response_model=list[CommentOut])
def list_comments(destination_id: str):
    _get_destination_or_404(destination_id)
    comments = [c for c in storage.read_all(storage.DESTINATION_COMMENTS_FILE) if c["destination_id"] == destination_id]
    comments.sort(key=lambda c: c["created_at"], reverse=True)
    return comments


@router.post("/{destination_id}/comments", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
def add_comment(destination_id: str, payload: CommentCreate, user: dict = Depends(get_current_user)):
    _get_destination_or_404(destination_id)
    comment = {
        "id": str(uuid.uuid4()),
        "destination_id": destination_id,
        "username": user["username"],
        "message": payload.message,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    storage.append(storage.DESTINATION_COMMENTS_FILE, comment)
    return comment


@router.delete("/{destination_id}/comments/{comment_id}")
def delete_comment(destination_id: str, comment_id: str, user: dict = Depends(get_current_user)):
    comments = storage.read_all(storage.DESTINATION_COMMENTS_FILE)
    comment = next((c for c in comments if c["id"] == comment_id and c["destination_id"] == destination_id), None)
    if not comment:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Comment not found")
    if comment["username"] != user["username"] and not user.get("is_admin", False):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only delete your own comments")

    storage.delete_one(storage.DESTINATION_COMMENTS_FILE, "id", comment_id)
    if user.get("is_admin", False) and comment["username"] != user["username"]:
        log_action(user["username"], "comment.moderated", target=destination_id, details=f"removed comment by {comment['username']}")
    return {"detail": "Comment deleted"}


# ---------------------------------------------------------------------------
# Admin: content enrichment from free external APIs (see app/enrichment.py)
# ---------------------------------------------------------------------------

@router.post("/{destination_id}/enrich", response_model=EnrichmentResult)
def enrich_one_destination(destination_id: str, admin: dict = Depends(require_permission("places"))):
    destination = _get_destination_or_404(destination_id)

    result = enrichment.enrich_destination(
        name=destination["name"],
        latitude=destination["latitude"],
        longitude=destination["longitude"],
        existing_images=destination.get("images") or ([destination["image_url"]] if destination.get("image_url") else []),
    )

    updates = {"enrichment_sources": result["enrichment_sources"], "enriched_at": datetime.now(timezone.utc).isoformat()}
    if result["description"]:
        updates["description"] = result["description"]
    if result["wiki_url"]:
        updates["wiki_url"] = result["wiki_url"]
    if result["images"]:
        updates["images"] = result["images"]
        if not destination.get("image_url"):
            updates["image_url"] = result["images"][0]
    if result["video_url"]:
        updates["video_url"] = result["video_url"]
    if result["rating"] is not None:
        updates["rating"] = result["rating"]
    if result["kinds"]:
        updates["kinds"] = result["kinds"]
    if result["how_to_get_there"]:
        updates["how_to_get_there"] = result["how_to_get_there"]

    storage.update_one(storage.DESTINATIONS_FILE, "id", destination_id, updates)
    log_action(admin["username"], "destination.enriched", target=destination_id, details=f"sources: {', '.join(result['enrichment_sources']) or 'none'}")

    updated = _get_destination_or_404(destination_id)
    return EnrichmentResult(
        destination_id=destination_id,
        updated_fields=list(updates.keys()),
        sources_used=result["enrichment_sources"],
        destination=Destination(**updated),
    )


@router.post("/enrich-all")
def enrich_all_destinations(limit: int = Query(default=20, ge=1, le=100), admin: dict = Depends(require_permission("places"))):
    """Bulk-enriches up to `limit` destinations that haven't been
    enriched yet. Capped and synchronous on purpose — free-tier APIs
    (Unsplash especially, 50 req/hr in dev mode) rate-limit hard, so
    running the whole catalogue at once would just start failing
    partway through. Call this repeatedly (e.g. from the admin
    dashboard, a few dozen at a time) rather than trying to do it all
    in one shot."""
    destinations = storage.read_all(storage.DESTINATIONS_FILE)
    todo = [d for d in destinations if not d.get("enriched_at")][:limit]

    results = []
    for d in todo:
        try:
            enriched = enrich_one_destination(d["id"], admin=admin)
            results.append({"id": d["id"], "name": d["name"], "status": "ok", "sources": enriched.sources_used})
        except Exception as exc:  # noqa: BLE001 — one bad destination shouldn't stop the batch
            results.append({"id": d["id"], "name": d["name"], "status": "failed", "error": str(exc)})

    return {"processed": len(results), "remaining": max(0, len([x for x in destinations if not x.get("enriched_at")]) - len(results)), "results": results}


@router.post("/seed")
def seed_destinations(limit: int = Query(default=5, ge=1, le=20), admin: dict = Depends(require_permission("places"))):
    result = seeding.seed_batch(limit=limit)
    log_action(
        admin["username"], "destinations.seeded",
        details=f"{result['processed']} imported this batch, {result['remaining']} remaining",
    )
    return result

