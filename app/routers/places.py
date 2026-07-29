"""
app/routers/places.py

Lets any authenticated user "advertise" a place: submit a new one, or
propose an update to an existing one. Submissions land in a separate
`places.json` queue with status=pending rather than merging straight
into the official destinations catalogue — an admin approves/rejects
them via the (Phase 2+) admin dashboard. This keeps the public catalogue
trustworthy while still letting users contribute.
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app import storage
from app.dependencies import get_current_admin, get_current_user
from app.notifications.service import create_notification
from app.schemas import PlaceSubmission

router = APIRouter(prefix="/places", tags=["places"])


@router.post("", status_code=status.HTTP_201_CREATED)
def submit_place(payload: PlaceSubmission, user: dict = Depends(get_current_user)):
    place = {
        "id": str(uuid.uuid4()),
        "status": "pending",  # pending | approved | rejected
        "submitted_by": user["username"],
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        **payload.model_dump(),
    }
    storage.append(storage.PLACES_FILE, place)
    return place


@router.get("/mine")
def list_my_submissions(user: dict = Depends(get_current_user)):
    places = storage.read_all(storage.PLACES_FILE)
    return [p for p in places if p["submitted_by"] == user["username"]]


@router.get("/pending")
def list_pending_submissions(admin: dict = Depends(get_current_admin)):
    places = storage.read_all(storage.PLACES_FILE)
    return [p for p in places if p["status"] == "pending"]


@router.post("/{place_id}/approve")
def approve_place(place_id: str, admin: dict = Depends(get_current_admin)):
    places = storage.read_all(storage.PLACES_FILE)
    place = next((p for p in places if p["id"] == place_id), None)
    if not place:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Submission not found")

    storage.update_one(storage.PLACES_FILE, "id", place_id, {"status": "approved"})

    # Promote into the public destinations catalogue.
    destination = {
        "id": place["id"],
        "name": place["name"],
        "region": place["region"],
        "tags": place["tags"],
        "description": place["description"],
        "image_url": place["image_url"],
        "latitude": place["latitude"],
        "longitude": place["longitude"],
        "avg_cost_fcfa": place.get("avg_cost_fcfa"),
        "submitted_by": place["submitted_by"],
    }
    storage.append(storage.DESTINATIONS_FILE, destination)
    create_notification(
        username=place["submitted_by"],
        title="Your place submission was approved!",
        message=f"'{place['name']}' is now live in the GT catalogue.",
        category="place",
    )
    return {"detail": "Approved and published", "destination_id": destination["id"]}


@router.post("/{place_id}/reject")
def reject_place(place_id: str, admin: dict = Depends(get_current_admin)):
    places = storage.read_all(storage.PLACES_FILE)
    place = next((p for p in places if p["id"] == place_id), None)
    if not place:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Submission not found")
    storage.update_one(storage.PLACES_FILE, "id", place_id, {"status": "rejected"})
    create_notification(
        username=place["submitted_by"],
        title="Your place submission was rejected",
        message=f"'{place['name']}' wasn't approved for the catalogue. Contact support for details.",
        category="place",
    )
    return {"detail": "Rejected"}
