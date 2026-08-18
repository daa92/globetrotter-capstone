"""
app/routers/feedback.py

Simple feedback intake. Feeds the (Phase 2+) admin dashboard so the
admin can see what users are reporting/requesting, and emails every
admin account (is_admin: true) so it doesn't require someone to be
actively watching the dashboard to notice new feedback.
"""
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app import storage
from app.dependencies import get_current_admin, get_current_user
from app.notifications import outbox
from app.schemas import FeedbackCreate

logger = logging.getLogger("gt.feedback")

router = APIRouter(prefix="/feedback", tags=["feedback"])


def _notify_admins(entry: dict) -> None:
    """Best-effort: a failed notification should never fail the feedback
    submission itself — the entry is already saved and visible in the
    dashboard regardless. Emails every admin account, not a single
    hardcoded address, so this keeps working if admins change."""
    admins = [u for u in storage.read_all(storage.USERS_FILE) if u.get("is_admin") and u.get("email")]
    if not admins:
        return

    rating_line = f"<p>Rating: {entry['rating']}/5</p>" if entry.get("rating") else ""
    body = (
        f"<p>New feedback from <strong>{entry['username']}</strong> "
        f"({entry['category']}):</p>"
        f"<p>{entry['message']}</p>"
        f"{rating_line}"
        f"<p><a href=\"https://gtcam.vercel.app/admin-c746b9c7d7c57420\">View in dashboard</a></p>"
    )
    for admin in admins:
        try:
            outbox.send(to=admin["email"], subject=f"New GT feedback: {entry['category']}", body=body)
        except Exception:  # noqa: BLE001 — never let a notification failure break submission
            logger.exception("Failed to notify admin %s of new feedback", admin["username"])


@router.post("", status_code=201)
def submit_feedback(payload: FeedbackCreate, user: dict = Depends(get_current_user)):
    entry = {
        "id": str(uuid.uuid4()),
        "username": user["username"],
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        **payload.model_dump(),
    }
    storage.append(storage.FEEDBACK_FILE, entry)
    _notify_admins(entry)
    return entry


@router.get("")
def list_feedback(admin: dict = Depends(get_current_admin)):
    """Admin-only: full feedback list feeds the hidden dashboard."""
    return storage.read_all(storage.FEEDBACK_FILE)
