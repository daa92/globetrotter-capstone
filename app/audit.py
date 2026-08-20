"""
app/audit.py

A single, append-only trail of "who did what to whom" — admin actions
(promote/revoke/permission changes, lock/unlock/delete, payout & place
decisions, notifications sent) plus a handful of security-relevant system
events (registration, verification, failed/locked login attempts), so the
admin dashboard has an actual answer to "what has been happening."

Deliberately dumb and synchronous: one row per event, no separate
service/queue. Given the existing storage layer is a single generic
`store` table already guarded by a process-local lock (see
app/storage.py), this adds negligible overhead and needs zero schema
migration — it's just another collection name.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from app import storage


def log_action(actor: str, action: str, target: Optional[str] = None, details: Optional[str] = None) -> dict:
    """
    actor:   username of whoever/whatever triggered this ('system' for
             automated background events like the unverified-account purge)
    action:  short machine-readable event name, e.g. 'admin.promote',
             'user.locked', 'login.failed', 'payout.approved'
    target:  the username or record id this event was about, if any
    details: free-text human-readable extra context
    """
    entry = {
        "id": str(uuid.uuid4()),
        "actor": actor,
        "action": action,
        "target": target,
        "details": details,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    storage.append(storage.AUDIT_LOG_FILE, entry)
    return entry
