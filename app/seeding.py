"""
app/seeding.py

The actual "import the curated Cameroon places list" logic, factored out
so it's callable two ways:
  - scripts/import_seed_places.py — one big local/CI run, all places at once
  - POST /admin/destinations/seed — small batches from the admin
    dashboard, so someone on Render's free tier (no shell access) can
    seed the catalogue with a button click instead of running a script
    from somewhere else entirely. Batched (not "do everything in one
    HTTP call") on purpose — a free hosting tier's request timeout and
    27 enrichment calls (each hitting up to 4 external APIs) don't mix
    well in one shot.
"""
import uuid
from datetime import datetime, timezone
from typing import Any

from app import enrichment, storage
from scripts.cameroon_places_seed import PLACES


def seed_status() -> dict:
    existing_names = {d["name"].lower() for d in storage.read_all(storage.DESTINATIONS_FILE)}
    remaining = [p for p in PLACES if p["name"].lower() not in existing_names]
    return {"total_in_seed_list": len(PLACES), "already_imported": len(PLACES) - len(remaining), "remaining": len(remaining)}


def seed_batch(limit: int = 5) -> dict[str, Any]:
    """Imports up to `limit` not-yet-imported places from the curated
    seed list, enriching each via the free external APIs (whichever
    are configured — see app/enrichment.py). Safe to call repeatedly;
    each call only ever touches places that aren't in the catalogue yet."""
    existing_names = {d["name"].lower() for d in storage.read_all(storage.DESTINATIONS_FILE)}
    todo = [p for p in PLACES if p["name"].lower() not in existing_names][:limit]

    results = []
    for place in todo:
        try:
            result = enrichment.enrich_destination(
                name=place["name"], latitude=place["latitude"], longitude=place["longitude"], existing_images=[],
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
                "submitted_by": None,
                "likes": 0,
                "dislikes": 0,
            }
            storage.append(storage.DESTINATIONS_FILE, destination)
            results.append({"name": place["name"], "status": "ok", "sources": result["enrichment_sources"]})
        except Exception as exc:  # noqa: BLE001 — one bad place shouldn't kill the batch
            results.append({"name": place["name"], "status": "failed", "error": str(exc)})

    status = seed_status()
    return {"processed": len(results), "remaining": status["remaining"], "results": results}
