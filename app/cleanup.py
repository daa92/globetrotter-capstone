"""
app/cleanup.py

"If a user attempts to register and doesn't get verified after 30
minutes, the system must delete all information concerning him."

Two pieces:
  - purge_unverified_users(): one pass, fully synchronous and unit-testable
    on its own — no server, no waiting, no mocking the clock needed beyond
    passing a `now` override.
  - run_cleanup_loop(): the recurring background task, started at app
    startup (see app/__init__.py's lifespan) and cancelled cleanly at
    shutdown so it never leaks between test runs or reloads.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from app import storage
from app.config import settings

logger = logging.getLogger("gt.cleanup")

# Exposed to the admin dashboard's system overview so "automatic operations
# happening in the background" (the unverified-account purge loop) are
# actually visible somewhere, not just inferred from logs.
_last_run_at: Optional[datetime] = None
_last_run_purged_count: int = 0
_run_count: int = 0


def get_cleanup_status() -> dict:
    return {
        "name": "unverified_account_cleanup",
        "description": "Deletes unverified accounts older than the TTL, on a fixed interval.",
        "interval_seconds": settings.VERIFICATION_CLEANUP_INTERVAL_SECONDS,
        "ttl_minutes": settings.UNVERIFIED_ACCOUNT_TTL_MINUTES,
        "run_count": _run_count,
        "last_run_at": _last_run_at.isoformat() if _last_run_at else None,
        "last_run_purged_count": _last_run_purged_count,
    }


def purge_unverified_users(now: Optional[datetime] = None) -> list[str]:
    """Deletes every unverified account whose registration is older than
    UNVERIFIED_ACCOUNT_TTL_MINUTES. Returns the usernames deleted."""
    now = now or datetime.now(timezone.utc)
    ttl = timedelta(minutes=settings.UNVERIFIED_ACCOUNT_TTL_MINUTES)

    users = storage.read_all(storage.USERS_FILE)
    to_delete = []
    to_keep = []

    for user in users:
        if user.get("is_verified", False):
            to_keep.append(user)
            continue
        created_at = datetime.fromisoformat(user["created_at"])
        if now - created_at > ttl:
            to_delete.append(user["username"])
        else:
            to_keep.append(user)

    if to_delete:
        storage.replace_all(storage.USERS_FILE, to_keep)
        logger.info("Purged %d unverified account(s): %s", len(to_delete), to_delete)
        from app import audit
        for username in to_delete:
            audit.log_action("system", "user.purged_unverified", target=username)

    return to_delete


async def run_cleanup_loop() -> None:
    """Runs purge_unverified_users() forever, on the configured interval,
    until cancelled (app shutdown)."""
    global _last_run_at, _last_run_purged_count, _run_count
    while True:
        try:
            deleted = purge_unverified_users()
            _last_run_at = datetime.now(timezone.utc)
            _last_run_purged_count = len(deleted)
            _run_count += 1
        except Exception:
            logger.exception("Unverified-account cleanup pass failed")
        await asyncio.sleep(settings.VERIFICATION_CLEANUP_INTERVAL_SECONDS)
