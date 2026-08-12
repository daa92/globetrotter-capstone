"""
app/notifications/outbox.py

A stand-in for a real email/SMS provider. When BREVO_API_KEY is set, email
messages are actually sent through Brevo's transactional email API; every
message (real or not) is still logged to data/outbox.json so registration/
verification stay testable offline, in CI, and in `pytest` (no network
calls or secrets needed there — BREVO_API_KEY is simply unset).

SMS is untouched — still outbox-only for now.
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

import httpx

from app import storage
from app.config import settings

logger = logging.getLogger(__name__)

BREVO_ENDPOINT = "https://api.brevo.com/v3/smtp/email"


def _send_via_brevo(to: str, subject: str, body: str) -> None:
    """Fire-and-log: a failed email should never break registration, since
    the user can always request a fresh verification link. We just log it."""
    try:
        response = httpx.post(
            BREVO_ENDPOINT,
            headers={
                "api-key": settings.BREVO_API_KEY,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            json={
                "sender": {"name": settings.BREVO_SENDER_NAME, "email": settings.BREVO_SENDER_EMAIL},
                "to": [{"email": to}],
                "subject": subject,
                "htmlContent": body,
            },
            timeout=10.0,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.error("Brevo send failed for %s: %s", to, exc)


def send(to: str, subject: str, body: str, channel: str = "email") -> dict:
    """channel: 'email' | 'sms'. Email actually sends via Brevo when
    BREVO_API_KEY is configured; SMS always just logs (no SMS provider yet).
    `body` is treated as HTML for email — callers building email bodies
    should write (or wrap) HTML accordingly."""
    if channel == "email" and settings.BREVO_API_KEY and settings.BREVO_SENDER_EMAIL:
        _send_via_brevo(to, subject, body)

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
