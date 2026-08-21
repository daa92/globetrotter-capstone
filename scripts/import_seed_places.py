"""
scripts/import_seed_places.py

CLI wrapper around app/seeding.py — imports every curated place from
cameroon_places_seed.py in one run. Kept as an option for local/CI use
(e.g. the GitHub Actions workflow), but for day-to-day use the admin
dashboard's "Seed starter destinations" button (POST
/admin/destinations/seed, batched) is the easier path — no shell
access anywhere required, just click it in the browser while logged in
as an admin.

Run this locally or in CI, with DATABASE_URL pointed at your TiDB instance:

    export DATABASE_URL="mysql+pymysql://user:password@host:4000/globetrotter"
    python -m scripts.import_seed_places

Safe to re-run: skips any place whose name already exists in the
destinations catalogue.
"""
import os
import sys
import time

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _BASE_DIR)

from app import db, seeding  # noqa: E402


def main() -> None:
    if not db.engine.url.get_backend_name().startswith("mysql"):
        print(f"WARNING: DATABASE_URL doesn't look like TiDB/MySQL (got: {db.engine.url}).")
        if input("Continue anyway? [y/N] ").strip().lower() != "y":
            print("Aborted.")
            return

    db.init_db()

    status = seeding.seed_status()
    print(f"{status['already_imported']} already in catalogue, {status['remaining']} to import.\n")

    total_imported = 0
    while True:
        batch = seeding.seed_batch(limit=5)
        for r in batch["results"]:
            if r["status"] == "ok":
                sources = ", ".join(r["sources"]) or "curated description only, no external sources matched"
                print(f"import {r['name']:<30} OK ({sources})")
                total_imported += 1
            else:
                print(f"import {r['name']:<30} FAILED ({r['error']})")
        if batch["remaining"] == 0:
            break
        time.sleep(1.5)  # be polite to free-tier rate limits between batches

    print(f"\nDone: {total_imported} imported.")


if __name__ == "__main__":
    main()
