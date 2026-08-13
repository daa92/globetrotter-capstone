"""
scripts/migrate_json_to_tidb.py

One-time migration: reads whatever's left in the local data/*.json files
and loads it into the new DB-backed storage (app/storage.py / app/db.py).

Run this ONCE, locally, with DATABASE_URL pointed at your TiDB instance,
BEFORE deleting the data/ directory:

    export DATABASE_URL="mysql+pymysql://user:password@host:4000/globetrotter"
    python -m scripts.migrate_json_to_tidb

Safe to re-run: each file's collection is fully replaced (not appended),
so running it twice with the same files just re-imports the same data.
Files that don't exist locally are skipped with a note — that's expected
for anything that only ever lived on Render's ephemeral disk (users,
itineraries, etc. created after your last local pull).
"""
import json
import os
import sys

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _BASE_DIR)

from app import db, storage  # noqa: E402

DATA_DIR = os.path.join(_BASE_DIR, "data")

# Maps each old JSON filename to its new collection constant.
FILES_TO_COLLECTIONS = {
    "users.json": storage.USERS_FILE,
    "itineraries.json": storage.ITINERARIES_FILE,
    "destinations.json": storage.DESTINATIONS_FILE,
    "places.json": storage.PLACES_FILE,
    "feedback.json": storage.FEEDBACK_FILE,
    "outbox.json": storage.OUTBOX_FILE,
    "activity.json": storage.ACTIVITY_FILE,
    "referrals.json": storage.REFERRALS_FILE,
    "payouts.json": storage.PAYOUTS_FILE,
    "notifications.json": storage.NOTIFICATIONS_FILE,
    "geo_cache.json": storage.GEO_CACHE_FILE,
}


def main() -> None:
    if not db.engine.url.get_backend_name().startswith("mysql"):
        print(
            "WARNING: DATABASE_URL doesn't look like a TiDB/MySQL URL "
            f"(got: {db.engine.url}). Set DATABASE_URL before running this, "
            "or you'll just migrate into a local SQLite file."
        )
        answer = input("Continue anyway? [y/N] ").strip().lower()
        if answer != "y":
            print("Aborted.")
            return

    db.init_db()

    migrated_any = False
    for filename, collection in FILES_TO_COLLECTIONS.items():
        path = os.path.join(DATA_DIR, filename)
        if not os.path.exists(path):
            print(f"skip  {filename:<20} (not found locally)")
            continue

        with open(path, "r", encoding="utf-8") as fh:
            content = fh.read().strip()
        records = json.loads(content) if content else []

        storage.replace_all(collection, records)
        print(f"OK    {filename:<20} -> {len(records)} record(s) into '{collection}'")
        migrated_any = True

    if not migrated_any:
        print("\nNothing found in data/ to migrate — nothing to do.")
    else:
        print("\nDone. Verify the data looks right (e.g. query the 'store' table, "
              "or hit GET /destinations on your API) before deleting data/.")


if __name__ == "__main__":
    main()
