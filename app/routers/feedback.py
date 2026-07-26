"""
app/routers/feedback.py

Simple feedback intake. Feeds the (Phase 2+) admin dashboard so the
admin can see what users are reporting/requesting.
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app import storage
from app.dependencies import get_current_admin, get_current_user
from app.schemas import FeedbackCreate

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("", status_code=201)
def submit_feedback(payload: FeedbackCreate, user: dict = Depends(get_current_user)):
    entry = {
        "id": str(uuid.uuid4()),
        "username": user["username"],
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        **payload.model_dump(),
    }
    storage.append(storage.FEEDBACK_FILE, entry)
    return entry


@router.get("")
def list_feedback(admin: dict = Depends(get_current_admin)):
    """Admin-only: full feedback list feeds the hidden dashboard."""
    return storage.read_all(storage.FEEDBACK_FILE)
