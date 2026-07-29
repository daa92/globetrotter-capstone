"""
app/notifications/service.py

The in-app notification feed (bell icon / notification center) — distinct
from app/notifications/outbox.py, which is the raw email/SMS channel.
A single event (e.g. "your payout was approved") often writes to both:
an in-app notification the user sees immediately, and optionally an email
via the outbox if they want/have one on file.
"""
import uuid
from datetime import datetime, timezone

from app import storage


def create_notification(username: str, title: str, message: str, category: str = "system", sent_by: str = "system") -> dict:
    notification = {
        "id": str(uuid.uuid4()),
        "username": username,
        "title": title,
        "message": message,
        "category": category,  # system | referral | payout | place | admin | security
        "is_read": False,
        "sent_by": sent_by,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    storage.append(storage.NOTIFICATIONS_FILE, notification)
    return notification


def create_for_many(usernames: list[str], title: str, message: str, category: str = "admin", sent_by: str = "admin") -> list[dict]:
    return [create_notification(u, title, message, category, sent_by) for u in usernames]
