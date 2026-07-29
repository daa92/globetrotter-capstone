"""
app/notifications/outbox.py

A stand-in for a real email/SMS provider. Every "sent" message is written
to data/outbox.json instead of actually leaving the machine — because a
real provider (SMTP, SendGrid, Twilio, etc.) needs paid/free-tier
credentials that don't belong hardcoded into a capstone repo, and this
keeps registration/verification fully testable offline, in CI, and in
`pytest`, with no network calls and no secrets.

Swapping this for a real provider later means rewriting exactly this one
function — nothing else in the app should ever construct an email/SMS
directly.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from app import storage


def send(to: str, subject: str, body: str, channel: str = "email") -> dict:
    """channel: 'email' | 'sms' — both just get logged to the outbox for now."""
    message = {
        "id": str(uuid.uuid4()),
        "channel": channel,
        "to": to,
        "subject": subject,
        "body": body,
        "sent_at": datetime.now(timezone.utc).isoformat(),
    }
    storage.append(storage.OUTBOX_FILE, message)
    return message


def get_last_message_to(to: str) -> Optional[dict]:
    """Convenience for tests/dev: fetch the most recent message sent to an address."""
    messages = [m for m in storage.read_all(storage.OUTBOX_FILE) if m["to"] == to]
    return messages[-1] if messages else None
