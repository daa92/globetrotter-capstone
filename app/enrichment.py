"""
app/enrichment.py

Pulls real-world content for a destination from free external APIs, so
places don't rely purely on manual data entry. Every source here is
free-tier and optional (see config.py) — if a key isn't set, that source
is silently skipped, not an error.

Sources used, and why:
  - Wikipedia REST API (no key, no rate limit in practice): description
    text and a canonical article link. Best free source for real prose
    about a named place.
  - Unsplash API (free tier, 50 req/hr in dev / 1000/hr once approved
    for production): high-quality photos by search query.
  - Pexels API (free tier, 200 req/hr): photos + *video* — Unsplash has
    no video, Pexels does, which is why both are wired in rather than
    just one.
  - OpenTripMap (free tier): POI metadata sourced from OpenStreetMap +
    Wikidata + Wikipedia — category ("kinds"), a 0–7 "rate" (their own
    notability/importance score, not a crowd rating), and a Wikipedia
    link as a description fallback when a place doesn't have its own
    Wikipedia page.
  - OpenRouteService (free tier, ~2000 req/day): real driving
    distance/duration from a reference city, for "how to get there".

What's deliberately NOT here: "how many people like/dislike this" or
star ratings from real visitors. No free API provides that — Google
Places, TripAdvisor, and Yelp all gate genuine crowd-sourced ratings
behind paid/restricted tiers, and that's especially true for smaller
Cameroonian locations that a free-tier POI database wouldn't have deep
review data on anyway. Building a fake number here would be worse than
not having one. Instead, likes/dislikes are first-party — see
`POST /destinations/{id}/like` etc. in app/routers/destinations.py —
genuine engagement from GT's own users, which is honest data instead of
an invented external number.
"""
import logging
import math
from urllib.parse import quote
from typing import Any, Optional

import httpx

from app.config import settings

logger = logging.getLogger("gt.enrichment")

_TIMEOUT = 8.0


def _get(url: str, **kwargs) -> Optional[httpx.Response]:
    """Every external call goes through this: never let one flaky provider
    break enrichment for the others, or break the place record update
    that's waiting on the result."""
    try:
        response = httpx.get(url, timeout=_TIMEOUT, **kwargs)
        response.raise_for_status()
        return response
    except httpx.HTTPError as exc:
        logger.warning("Enrichment call failed: %s (%s)", url, exc)
        return None


def fetch_wikipedia_summary(name: str) -> Optional[dict[str, str]]:
    """No API key needed. Returns {"description": ..., "wiki_url": ...} or None."""
    # Wikipedia's convention: spaces -> underscores in the path segment,
    # then percent-encode. Getting this wrong silently 404s on any
    # multi-word place name, which is most of them.
    title = quote(name.replace(" ", "_"))
    response = _get(
        f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}",
        headers={"User-Agent": "GlobeTrotter-Cameroon/1.0 (capstone project)"},
    )
    if response is None:
        return None
    data = response.json()
    if data.get("type") == "disambiguation" or not data.get("extract"):
        return None
    return {
        "description": data["extract"],
        "wiki_url": data.get("content_urls", {}).get("desktop", {}).get("page"),
    }


def fetch_unsplash_images(query: str, count: int = 3) -> list[str]:
    if not settings.UNSPLASH_ACCESS_KEY:
        return []
    response = _get(
        "https://api.unsplash.com/search/photos",
        params={"query": f"{query} Cameroon", "per_page": count},
        headers={"Authorization": f"Client-ID {settings.UNSPLASH_ACCESS_KEY}"},
    )
    if response is None:
        return []
    return [r["urls"]["regular"] for r in response.json().get("results", [])[:count]]


def fetch_pexels_photos_and_video(query: str) -> dict[str, Any]:
    """One combined call since Pexels' photo and video endpoints are
    separate but we always want both from the same provider/key."""
    if not settings.PEXELS_API_KEY:
        return {"images": [], "video_url": None}

    headers = {"Authorization": settings.PEXELS_API_KEY}
    images: list[str] = []
    video_url = None

    photos = _get(
        "https://api.pexels.com/v1/search",
        params={"query": f"{query} Cameroon", "per_page": 3},
        headers=headers,
    )
    if photos is not None:
        images = [p["src"]["large"] for p in photos.json().get("photos", [])]

    videos = _get(
        "https://api.pexels.com/videos/search",
        params={"query": f"{query} Cameroon", "per_page": 1},
        headers=headers,
    )
    if videos is not None:
        results = videos.json().get("videos", [])
        if results:
            # Prefer a mid-resolution file (smaller payload) over the
            # first entry, which is often a huge 4K file.
            files = sorted(results[0].get("video_files", []), key=lambda f: f.get("width", 0))
            mid = files[len(files) // 2] if files else None
            video_url = mid["link"] if mid else results[0].get("video_files", [{}])[0].get("link")

    return {"images": images, "video_url": video_url}


def fetch_opentripmap_poi(name: str, latitude: float, longitude: float) -> Optional[dict[str, Any]]:
    """Finds the nearest matching POI to the given coordinates and
    returns its category, rating, image, and description fallback."""
    if not settings.OPENTRIPMAP_API_KEY:
        return None

    nearby = _get(
        "https://api.opentripmap.com/0.1/en/places/radius",
        params={
            "radius": 3000,
            "lat": latitude,
            "lon": longitude,
            "name": name,
            "limit": 1,
            "apikey": settings.OPENTRIPMAP_API_KEY,
        },
    )
    if nearby is None:
        return None
    features = nearby.json().get("features", [])
    if not features:
        return None

    xid = features[0]["properties"]["xid"]
    details = _get(f"https://api.opentripmap.com/0.1/en/places/xid/{xid}", params={"apikey": settings.OPENTRIPMAP_API_KEY})
    if details is None:
        return None
    d = details.json()

    # OpenTripMap's "rate" is 0-7 (their own notability score, not a
    # crowd rating — see module docstring). Normalize to a 0-5 scale so
    # the frontend has one consistent star range regardless of source.
    raw_rate = d.get("rate")
    normalized_rating = round((raw_rate / 7) * 5, 1) if isinstance(raw_rate, (int, float)) and raw_rate > 0 else None

    return {
        "kinds": d.get("kinds", "").split(",") if d.get("kinds") else [],
        "rating": normalized_rating,
        "image": d.get("preview", {}).get("source") or d.get("image"),
        "description": d.get("wikipedia_extracts", {}).get("text"),
        "wiki_url": d.get("wikipedia"),
    }


def fetch_directions_from_reference_city(latitude: float, longitude: float) -> Optional[dict[str, Any]]:
    """Real driving distance/duration from the configured reference city
    (default: Douala). Falls back to straight-line (haversine) distance
    with no key configured, since that needs no API at all."""
    straight_line_km = _haversine_km(settings.REFERENCE_CITY_LAT, settings.REFERENCE_CITY_LON, latitude, longitude)

    if not settings.OPENROUTESERVICE_API_KEY:
        return {
            "from": settings.REFERENCE_CITY_NAME,
            "distance_km": round(straight_line_km, 1),
            "duration_minutes": None,
            "method": "straight_line",
        }

    response = _get(
        "https://api.openrouteservice.org/v2/directions/driving-car",
        params={
            "api_key": settings.OPENROUTESERVICE_API_KEY,
            "start": f"{settings.REFERENCE_CITY_LON},{settings.REFERENCE_CITY_LAT}",
            "end": f"{longitude},{latitude}",
        },
    )
    if response is None:
        return {
            "from": settings.REFERENCE_CITY_NAME,
            "distance_km": round(straight_line_km, 1),
            "duration_minutes": None,
            "method": "straight_line",
        }

    summary = response.json()["features"][0]["properties"]["summary"]
    return {
        "from": settings.REFERENCE_CITY_NAME,
        "distance_km": round(summary["distance"] / 1000, 1),
        "duration_minutes": round(summary["duration"] / 60),
        "method": "driving",
    }


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def enrich_destination(name: str, latitude: float, longitude: float, existing_images: list[str]) -> dict[str, Any]:
    """The orchestration entry point — combines every source above into
    one merged result, admin-facing endpoint calls exactly this. Sources
    are layered with sensible fallback priority rather than overwriting
    each other blindly:
      description: Wikipedia direct match > OpenTripMap's Wikipedia extract
      images: existing (never dropped) + Unsplash + Pexels, deduped
      rating: OpenTripMap only (the one source that has anything like it)
    """
    wiki = fetch_wikipedia_summary(name)
    otm = fetch_opentripmap_poi(name, latitude, longitude)
    pexels = fetch_pexels_photos_and_video(name)
    unsplash_images = fetch_unsplash_images(name)
    directions = fetch_directions_from_reference_city(latitude, longitude)

    description = (wiki or {}).get("description") or (otm or {}).get("description")
    wiki_url = (wiki or {}).get("wiki_url") or (otm or {}).get("wiki_url")

    new_images = unsplash_images + pexels["images"]
    if otm and otm.get("image"):
        new_images.append(otm["image"])
    all_images = list(dict.fromkeys(existing_images + new_images))  # de-dupe, preserve order

    return {
        "description": description,
        "wiki_url": wiki_url,
        "images": all_images,
        "video_url": pexels.get("video_url"),
        "rating": (otm or {}).get("rating"),
        "kinds": (otm or {}).get("kinds", []),
        "how_to_get_there": directions,
        "enrichment_sources": [
            s for s, present in [
                ("wikipedia", bool(wiki)),
                ("opentripmap", bool(otm)),
                ("unsplash", bool(unsplash_images)),
                ("pexels", bool(pexels["images"] or pexels["video_url"])),
                ("openrouteservice", directions is not None and directions.get("method") == "driving"),
            ] if present
        ],
    }
