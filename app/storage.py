"""
app/storage.py

Phase 1 persistence: plain JSON files under /data.

This is intentionally the "naive" storage layer the capstone asks for in
Phase 1 (no database yet). It is deliberately isolated behind small,
single-purpose functions so that swapping it for a real database in
Phase 2 only means rewriting this file — no router/business-logic code
should ever touch the filesystem directly.

NOT thread-safe beyond a simple in-process lock. That's expected: it's a
documented limitation of Phase 1 (see README "Known Limitations"), one of
the exact pain points the capstone wants you to experience.
"""
import json
import os
import threading
from typing import Any

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(_BASE_DIR, "data")

USERS_FILE = os.path.join(DATA_DIR, "users.json")
ITINERARIES_FILE = os.path.join(DATA_DIR, "itineraries.json")
DESTINATIONS_FILE = os.path.join(DATA_DIR, "destinations.json")
PLACES_FILE = os.path.join(DATA_DIR, "places.json")
FEEDBACK_FILE = os.path.join(DATA_DIR, "feedback.json")
OUTBOX_FILE = os.path.join(DATA_DIR, "outbox.json")
ACTIVITY_FILE = os.path.join(DATA_DIR, "activity.json")
REFERRALS_FILE = os.path.join(DATA_DIR, "referrals.json")
PAYOUTS_FILE = os.path.join(DATA_DIR, "payouts.json")

_lock = threading.Lock()


def _read_json(filepath: str) -> list[dict[str, Any]]:
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r", encoding="utf-8") as fh:
        content = fh.read().strip()
        return json.loads(content) if content else []


def _write_json(filepath: str, data: list[dict[str, Any]]) -> None:
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    tmp_path = f"{filepath}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
    os.replace(tmp_path, filepath)  # atomic-ish swap, avoids half-written files


# ---------------------------------------------------------------------------
# Generic collection helpers
# ---------------------------------------------------------------------------

def read_all(filepath: str) -> list[dict[str, Any]]:
    with _lock:
        return _read_json(filepath)


def append(filepath: str, record: dict[str, Any]) -> None:
    with _lock:
        records = _read_json(filepath)
        records.append(record)
        _write_json(filepath, records)


def replace_all(filepath: str, records: list[dict[str, Any]]) -> None:
    with _lock:
        _write_json(filepath, records)


def update_one(filepath: str, match_key: str, match_value: Any, updates: dict[str, Any]) -> bool:
    """Update the first record where record[match_key] == match_value. Returns True if found."""
    with _lock:
        records = _read_json(filepath)
        for record in records:
            if record.get(match_key) == match_value:
                record.update(updates)
                _write_json(filepath, records)
                return True
        return False


def delete_one(filepath: str, match_key: str, match_value: Any) -> bool:
    with _lock:
        records = _read_json(filepath)
        new_records = [r for r in records if r.get(match_key) != match_value]
        if len(new_records) == len(records):
            return False
        _write_json(filepath, new_records)
        return True
