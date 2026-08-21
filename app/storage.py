"""
app/storage.py

Phase 2 persistence: TiDB (MySQL-compatible), through the single generic
`store` table defined in app/db.py.

This is a drop-in replacement for the old JSON-file version: every
function below keeps the exact same name, signature, and behavior, so no
router or business-logic code anywhere else in the app needed to change
— they still just do things like storage.read_all(storage.USERS_FILE).

The "_FILE" constants now hold a logical *collection name* string instead
of a filesystem path. The name was kept (rather than renamed to
"_COLLECTION") purely to avoid touching every call site across the app.
"""
import json
import threading
from typing import Any

from sqlalchemy import delete, insert, select, update

from app import db

USERS_FILE = "users"
ITINERARIES_FILE = "itineraries"
DESTINATIONS_FILE = "destinations"
PLACES_FILE = "places"
FEEDBACK_FILE = "feedback"
OUTBOX_FILE = "outbox"
ACTIVITY_FILE = "activity"
REFERRALS_FILE = "referrals"
PAYOUTS_FILE = "payouts"
NOTIFICATIONS_FILE = "notifications"
NOTIFICATION_BATCHES_FILE = "notification_batches"
AUDIT_LOG_FILE = "audit_log"
GEO_CACHE_FILE = "geo_cache"
DESTINATION_VOTES_FILE = "destination_votes"

# A process-local lock still guards read-modify-write sequences, matching
# the old file-based version's documented limitation (see its original
# docstring). Real cross-process/cross-instance safety would need
# SELECT ... FOR UPDATE row locking — a reasonable next step, but out of
# scope for this swap; Render's free/starter tiers run a single instance
# anyway.
_lock = threading.Lock()


def _normalize(data: Any) -> dict[str, Any]:
    """SQLite stores JSON as TEXT (returned as a str); MySQL/TiDB's JSON
    type round-trips as a dict already. Handle both so this file doesn't
    care which backend is active."""
    return json.loads(data) if isinstance(data, str) else data


def _select_rows(conn, collection: str) -> list[tuple[int, dict]]:
    rows = conn.execute(
        select(db.store.c.id, db.store.c.data)
        .where(db.store.c.collection == collection)
        .order_by(db.store.c.id)
    ).all()
    return [(row.id, _normalize(row.data)) for row in rows]


# ---------------------------------------------------------------------------
# Generic collection helpers
# ---------------------------------------------------------------------------

def read_all(collection: str) -> list[dict[str, Any]]:
    with _lock, db.engine.begin() as conn:
        return [data for _, data in _select_rows(conn, collection)]


def append(collection: str, record: dict[str, Any]) -> None:
    with _lock, db.engine.begin() as conn:
        conn.execute(insert(db.store).values(collection=collection, data=record))


def replace_all(collection: str, records: list[dict[str, Any]]) -> None:
    with _lock, db.engine.begin() as conn:
        conn.execute(delete(db.store).where(db.store.c.collection == collection))
        if records:
            conn.execute(
                insert(db.store),
                [{"collection": collection, "data": r} for r in records],
            )


def update_one(collection: str, match_key: str, match_value: Any, updates: dict[str, Any]) -> bool:
    """Update the first record where record[match_key] == match_value. Returns True if found."""
    with _lock, db.engine.begin() as conn:
        for row_id, data in _select_rows(conn, collection):
            if data.get(match_key) == match_value:
                data.update(updates)
                conn.execute(update(db.store).where(db.store.c.id == row_id).values(data=data))
                return True
        return False


def delete_one(collection: str, match_key: str, match_value: Any) -> bool:
    with _lock, db.engine.begin() as conn:
        for row_id, data in _select_rows(conn, collection):
            if data.get(match_key) == match_value:
                conn.execute(delete(db.store).where(db.store.c.id == row_id))
                return True
        return False


def update_many(collection: str, match_key: str, match_values: set, updates: dict[str, Any]) -> int:
    """Update every record whose record[match_key] is in match_values. Returns count updated."""
    with _lock, db.engine.begin() as conn:
        count = 0
        for row_id, data in _select_rows(conn, collection):
            if data.get(match_key) in match_values:
                data.update(updates)
                conn.execute(update(db.store).where(db.store.c.id == row_id).values(data=data))
                count += 1
        return count


def delete_many(collection: str, match_key: str, match_values: set) -> int:
    with _lock, db.engine.begin() as conn:
        ids_to_delete = [
            row_id for row_id, data in _select_rows(conn, collection) if data.get(match_key) in match_values
        ]
        if ids_to_delete:
            conn.execute(delete(db.store).where(db.store.c.id.in_(ids_to_delete)))
        return len(ids_to_delete)
