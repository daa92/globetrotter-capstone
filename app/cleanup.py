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

    return to_delete


async def run_cleanup_loop() -> None:
    """Runs purge_unverified_users() forever, on the configured interval,
    until cancelled (app shutdown)."""
    while True:
        try:
            purge_unverified_users()
        except Exception:
            logger.exception("Unverified-account cleanup pass failed")
        await asyncio.sleep(settings.VERIFICATION_CLEANUP_INTERVAL_SECONDS)
