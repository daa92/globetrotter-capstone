"""
app/routers/places.py

Lets any authenticated user submit a place: name, description, region,
tags, coordinates, optional price info, and optional media (images
and/or a video, combined max 10MB — see app/media.py).

Approval rules:
  - Admin-submitted places publish immediately, no approval step.
  - Everyone else's submissions land as status=pending until an admin
    with the "places" permission approves or rejects them.

A single record in PLACES_FILE is the source of truth for a
user-submitted place through its whole lifecycle (pending -> approved/
rejected -> edited -> deleted). Once approved, a matching copy also
exists in DESTINATIONS_FILE (same id) so the public /destinations search
doesn't need to know about pending/rejected submissions at all. Edits
and deletes touch both records when both exist, keeping them in sync
without needing a bigger schema/search rewrite.
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app import audit, media, storage
from app.config import settings
from app.dependencies import get_current_user, require_permission
from app.notifications.service import create_notification
from app.schemas import MediaUploadResponse, PlaceSubmission, PlaceUpdate

router = APIRouter(prefix="/places", tags=["places"])


# ---------------------------------------------------------------------------
# Media upload — called before place creation/edit; the place endpoints
# themselves only ever deal with the resulting URLs, never raw bytes.
# ---------------------------------------------------------------------------

@router.post("/upload-media", response_model=MediaUploadResponse)
async def upload_media(files: list[UploadFile] = File(default=[]), user: dict = Depends(get_current_user)):
    if not media.is_configured():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Media uploads aren't configured on this server yet")

    if not files:
        return MediaUploadResponse(images=[], video_url=None, total_bytes=0)

    # Read everything up front so we can enforce the combined 10MB cap
    # BEFORE uploading anything — no point burning upload calls (and
    # Cloudinary quota) on a submission we're going to reject anyway.
    contents = [await f.read() for f in files]
    total_bytes = sum(len(c) for c in contents)
    if total_bytes > settings.MAX_PLACE_MEDIA_BYTES:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"Combined file size {total_bytes / 1_000_000:.1f}MB exceeds the 10MB limit",
        )

    images: list[str] = []
    video_url = None
    for f, content in zip(files, contents):
        content_type = f.content_type or ""
        if not (content_type.startswith("image/") or content_type.startswith("video/")):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"'{f.filename}' isn't an image or video ({content_type or 'unknown type'})")
        try:
            result = media.upload_file(content, f.filename or "upload", content_type)
        except media.MediaUploadError as exc:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc

        if result["resource_type"] == "video":
            video_url = result["url"]  # last video wins if somehow more than one was sent
        else:
            images.append(result["url"])

    return MediaUploadResponse(images=images, video_url=video_url, total_bytes=total_bytes)


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

@router.post("", status_code=status.HTTP_201_CREATED)
def submit_place(payload: PlaceSubmission, user: dict = Depends(get_current_user)):
    is_admin = user.get("is_admin", False)
    now = datetime.now(timezone.utc).isoformat()

    place = {
        "id": str(uuid.uuid4()),
        "status": "approved" if is_admin else "pending",
        "submitted_by": user["username"],
        "submitted_at": now,
        "updated_at": now,
        **payload.model_dump(),
    }
    storage.append(storage.PLACES_FILE, place)

    if is_admin:
        _publish_to_destinations(place)
        audit.log_action(user["username"], "place.self_published", target=place["name"], details="admin submission, no approval required")
    else:
        audit.log_action(user["username"], "place.submitted", target=place["name"], details="awaiting admin approval")

    return place


def _publish_to_destinations(place: dict) -> None:
    destination = {
        "id": place["id"],
        "name": place["name"],
        "region": place["region"],
        "tags": place["tags"],
        "description": place["description"],
        "image_url": (place.get("images") or [""])[0],
        "images": place.get("images", []),
        "video_url": place.get("video_url"),
        "latitude": place["latitude"],
        "longitude": place["longitude"],
        "avg_cost_fcfa": place.get("avg_cost_fcfa"),
        "price_list": place.get("price_list", []),
        "submitted_by": place["submitted_by"],
    }
    # Overwrite if a destination with this id already exists (edit-after-
    # publish path), otherwise add it fresh.
    existing = storage.read_all(storage.DESTINATIONS_FILE)
    if any(d["id"] == place["id"] for d in existing):
        storage.update_one(storage.DESTINATIONS_FILE, "id", place["id"], destination)
    else:
        storage.append(storage.DESTINATIONS_FILE, destination)


def _unpublish_from_destinations(place_id: str) -> None:
    storage.delete_one(storage.DESTINATIONS_FILE, "id", place_id)


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------

@router.get("/mine")
def list_my_submissions(user: dict = Depends(get_current_user)):
    places = storage.read_all(storage.PLACES_FILE)
    return [p for p in places if p["submitted_by"] == user["username"]]


@router.get("/pending")
def list_pending_submissions(admin: dict = Depends(require_permission("places"))):
    places = storage.read_all(storage.PLACES_FILE)
    return [p for p in places if p["status"] == "pending"]


def _get_place_or_404(place_id: str) -> dict:
    places = storage.read_all(storage.PLACES_FILE)
    place = next((p for p in places if p["id"] == place_id), None)
    if not place:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Submission not found")
    return place


def _require_owner_or_admin(place: dict, user: dict) -> None:
    if place["submitted_by"] != user["username"] and not user.get("is_admin", False):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only edit or delete your own place submissions")


# ---------------------------------------------------------------------------
# Edit — owner or admin. A non-admin owner editing an already-approved
# place sends it back to pending (re-review), matching the rule that
# only admins can put content live without approval. Admin edits never
# require re-approval and publish/update immediately.
# ---------------------------------------------------------------------------

@router.patch("/{place_id}")
def edit_place(place_id: str, payload: PlaceUpdate, user: dict = Depends(get_current_user)):
    place = _get_place_or_404(place_id)
    _require_owner_or_admin(place, user)

    is_admin = user.get("is_admin", False)
    updates = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()

    was_approved = place["status"] == "approved"

    if is_admin:
        # Admin bypasses approval entirely — publish/update immediately,
        # whatever the previous status was.
        updates["status"] = "approved"
    elif was_approved:
        # Non-admin editing already-live content: pull it back offline
        # until re-reviewed, so a bad edit can't slip out silently.
        updates["status"] = "pending"

    storage.update_one(storage.PLACES_FILE, "id", place_id, updates)
    updated_place = _get_place_or_404(place_id)

    if updated_place["status"] == "approved":
        _publish_to_destinations(updated_place)
    elif was_approved and updated_place["status"] == "pending":
        _unpublish_from_destinations(place_id)  # pulled offline pending re-review

    audit.log_action(user["username"], "place.edited", target=updated_place["name"], details=f"status now {updated_place['status']}")

    if was_approved and updated_place["status"] == "pending":
        create_notification(
            username=place["submitted_by"],
            title="Your edit needs re-approval",
            message=f"'{updated_place['name']}' was taken offline until an admin reviews your changes.",
            category="place",
        )

    return updated_place


# ---------------------------------------------------------------------------
# Delete — owner or admin, removes both the submission record and its
# published destination copy (if any).
# ---------------------------------------------------------------------------

@router.delete("/{place_id}")
def delete_place(place_id: str, user: dict = Depends(get_current_user)):
    place = _get_place_or_404(place_id)
    _require_owner_or_admin(place, user)

    storage.delete_one(storage.PLACES_FILE, "id", place_id)
    _unpublish_from_destinations(place_id)

    for url in place.get("images", []):
        media.delete_file(_public_id_from_url(url), "image")
    if place.get("video_url"):
        media.delete_file(_public_id_from_url(place["video_url"]), "video")

    audit.log_action(user["username"], "place.deleted", target=place["name"])
    return {"detail": f"'{place['name']}' deleted"}


def _public_id_from_url(url: str) -> str:
    """Cloudinary public_id is the URL path after the version segment,
    minus the extension — reconstructed here since we only stored the
    URL, not the public_id, at upload time (kept the upload response
    minimal on purpose)."""
    try:
        after_upload = url.split("/upload/", 1)[1]
        parts = after_upload.split("/", 1)
        path = parts[1] if len(parts) > 1 and parts[0].startswith("v") else after_upload
        return path.rsplit(".", 1)[0]
    except (IndexError, AttributeError):
        return ""


# ---------------------------------------------------------------------------
# Admin moderation — approve/reject a pending submission.
# ---------------------------------------------------------------------------

@router.post("/{place_id}/approve")
def approve_place(place_id: str, admin: dict = Depends(require_permission("places"))):
    place = _get_place_or_404(place_id)
    storage.update_one(storage.PLACES_FILE, "id", place_id, {"status": "approved"})
    updated = _get_place_or_404(place_id)
    _publish_to_destinations(updated)

    audit.log_action(admin["username"], "place.approved", target=place["name"], details=f"submitted by {place['submitted_by']}")
    create_notification(
        username=place["submitted_by"],
        title="Your place submission was approved!",
        message=f"'{place['name']}' is now live in the GT catalogue.",
        category="place",
    )
    return {"detail": "Approved and published", "destination_id": place["id"]}


@router.post("/{place_id}/reject")
def reject_place(place_id: str, admin: dict = Depends(require_permission("places"))):
    place = _get_place_or_404(place_id)
    storage.update_one(storage.PLACES_FILE, "id", place_id, {"status": "rejected"})
    _unpublish_from_destinations(place_id)
    audit.log_action(admin["username"], "place.rejected", target=place["name"], details=f"submitted by {place['submitted_by']}")
    create_notification(
        username=place["submitted_by"],
        title="Your place submission was rejected",
        message=f"'{place['name']}' wasn't approved for the catalogue. Contact support for details.",
        category="place",
    )
    return {"detail": "Rejected"}
