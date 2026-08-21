"""
scripts/import_seed_places.py

Seeds the curated list in cameroon_places_seed.py into the live
destinations catalogue, enriching each one via app/enrichment.py
(Wikipedia description, Unsplash/Pexels photos, OpenTripMap rating,
OpenRouteService directions — whichever of those you've configured;
none are required, see HOW_TO_APPLY.md).

Run this ONCE, locally, with DATABASE_URL pointed at your TiDB instance:

    export DATABASE_URL="mysql+pymysql://user:password@host:4000/globetrotter"
    python -m scripts.import_seed_places

Safe to re-run: skips any place whose name already exists in the
destinations catalogue, so running it again after adding new entries to
cameroon_places_seed.py only imports the new ones.
"""
import os
import sys
import time
import uuid
from datetime import datetime, timezone

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _BASE_DIR)

from app import db, enrichment, storage  # noqa: E402
from scripts.cameroon_places_seed import PLACES  # noqa: E402


def main() -> None:
    if not db.engine.url.get_backend_name().startswith("mysql"):
        print(f"WARNING: DATABASE_URL doesn't look like TiDB/MySQL (got: {db.engine.url}).")
        if input("Continue anyway? [y/N] ").strip().lower() != "y":
            print("Aborted.")
            return

    db.init_db()

    existing_names = {d["name"].lower() for d in storage.read_all(storage.DESTINATIONS_FILE)}
    imported, skipped = 0, 0

    for place in PLACES:
        if place["name"].lower() in existing_names:
            print(f"skip   {place['name']:<30} (already in catalogue)")
            skipped += 1
            continue

        print(f"import {place['name']:<30} ", end="", flush=True)
        result = enrichment.enrich_destination(
            name=place["name"],
            latitude=place["latitude"],
            longitude=place["longitude"],
            existing_images=[],
        )

        destination = {
            "id": str(uuid.uuid4()),
            "name": place["name"],
            "region": place["region"],
            "tags": place["tags"],
            "description": result["description"] or place["description"],
            "image_url": (result["images"][0] if result["images"] else ""),
            "images": result["images"],
            "video_url": result["video_url"],
            "wiki_url": result["wiki_url"],
            "kinds": result["kinds"],
            "rating": result["rating"],
            "how_to_get_there": result["how_to_get_there"],
            "enrichment_sources": result["enrichment_sources"],
            "enriched_at": datetime.now(timezone.utc).isoformat(),
            "latitude": place["latitude"],
            "longitude": place["longitude"],
            "avg_cost_fcfa": place.get("avg_cost_fcfa"),
            "price_list": [],
            "submitted_by": None,  # official seed data, not a user submission
            "likes": 0,
            "dislikes": 0,
        }
        storage.append(storage.DESTINATIONS_FILE, destination)
        imported += 1
        sources = ", ".join(result["enrichment_sources"]) or "curated description only, no external sources matched"
        print(f"OK ({sources})")

        # Be polite to free-tier rate limits (Unsplash: 50/hr in dev
        # mode) — a short pause between places costs a few minutes total
        # for this list, and avoids tripping a rate limit partway through.
        time.sleep(1.5)

    print(f"\nDone: {imported} imported, {skipped} already present.")


if __name__ == "__main__":
    main()
