"""
app/geo_service.py

The free, Cameroon-scoped map/geo stack:
  - Nominatim  -> place search/geocoding (no API key, 1 req/sec policy)
  - Overpass   -> points-of-interest search (no API key)
  - OpenRouteService -> walking/driving/cycling directions (free API key,
    2,000 requests/day)

Every one of these has a strict or courtesy rate limit, and none of them
want to be called live on every single user request — so every public
function here is a thin cached wrapper around an isolated `_fetch_*`
function. That isolation is deliberate: it's the one seam tests monkeypatch
(a live call needs real network access to these services, which a test
suite should never depend on), and it's the one place to swap
implementations later (e.g. self-hosting Nominatim once traffic justifies it).
"""
import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

import httpx

from app import storage
from app.config import settings


# ---------------------------------------------------------------------------
# Generic cache wrapper
# ---------------------------------------------------------------------------

def _cache_key(namespace: str, **params: Any) -> str:
    raw = namespace + "|" + json.dumps(params, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()


def _get_cached(key: str, ttl_hours: int) -> Any:
    entries = storage.read_all(storage.GEO_CACHE_FILE)
    entry = next((e for e in entries if e["key"] == key), None)
    if not entry:
        return None
    cached_at = datetime.fromisoformat(entry["cached_at"])
    if datetime.now(timezone.utc) - cached_at > timedelta(hours=ttl_hours):
        return None
    return entry["value"]


def _set_cached(key: str, value: Any) -> None:
    entries = storage.read_all(storage.GEO_CACHE_FILE)
    entries = [e for e in entries if e["key"] != key]
    entries.append({"key": key, "value": value, "cached_at": datetime.now(timezone.utc).isoformat()})
    storage.replace_all(storage.GEO_CACHE_FILE, entries)


def get_or_fetch(namespace: str, fetch_fn: Callable, ttl_hours: int | None = None, **params: Any) -> tuple[Any, bool]:
    """Returns (value, was_cached). Only calls fetch_fn on a cache miss/stale entry."""
    ttl_hours = settings.GEO_CACHE_TTL_HOURS if ttl_hours is None else ttl_hours
    key = _cache_key(namespace, **params)
    cached = _get_cached(key, ttl_hours)
    if cached is not None:
        return cached, True
    value = fetch_fn(**params)
    _set_cached(key, value)
    return value, False


# ---------------------------------------------------------------------------
# Nominatim — place search / geocoding
# ---------------------------------------------------------------------------

def _fetch_nominatim_search(query: str) -> list[dict]:
    resp = httpx.get(
        f"{settings.NOMINATIM_BASE_URL}/search",
        params={
            "q": query,
            "format": "jsonv2",
            "countrycodes": "cm",
            "viewbox": settings.CAMEROON_VIEWBOX,
            "bounded": 1,
            "limit": 10,
        },
        headers={"User-Agent": settings.GEO_USER_AGENT},
        timeout=10,
    )
    resp.raise_for_status()
    return [
        {
            "name": r.get("name") or r["display_name"].split(",")[0],
            "display_name": r["display_name"],
            "latitude": float(r["lat"]),
            "longitude": float(r["lon"]),
            "type": r.get("type"),
        }
        for r in resp.json()
    ]


def search_places(query: str) -> tuple[list[dict], bool]:
    return get_or_fetch("nominatim_search", _fetch_nominatim_search, query=query)


# ---------------------------------------------------------------------------
# OpenRouteService — walking / driving / cycling directions
# ---------------------------------------------------------------------------

def _fetch_route(start_lat: float, start_lng: float, end_lat: float, end_lng: float, profile: str) -> dict:
    resp = httpx.get(
        f"{settings.OPENROUTESERVICE_BASE_URL}/v2/directions/{profile}",
        params={
            "api_key": settings.OPENROUTESERVICE_API_KEY,
            "start": f"{start_lng},{start_lat}",
            "end": f"{end_lng},{end_lat}",
        },
        timeout=10,
    )
    resp.raise_for_status()
    summary = resp.json()["features"][0]["properties"]["summary"]
    return {
        "distance_km": round(summary["distance"] / 1000, 2),
        "duration_minutes": round(summary["duration"] / 60, 1),
        "profile": profile,
    }


def get_route(start_lat: float, start_lng: float, end_lat: float, end_lng: float, profile: str = "foot-walking") -> tuple[dict, bool]:
    return get_or_fetch(
        "ors_route", _fetch_route,
        start_lat=start_lat, start_lng=start_lng, end_lat=end_lat, end_lng=end_lng, profile=profile,
    )


# ---------------------------------------------------------------------------
# Overpass — points of interest (restaurants, hospitals, fuel, etc.)
#
# OpenStreetMap doesn't tag everything under "amenity" — a restaurant is
# amenity=restaurant, but a hotel is tourism=hotel, an airport is
# aeroway=aerodrome, and a supermarket is shop=supermarket. Treating
# every category as "amenity=X" (an earlier version of this file did)
# silently returns zero results for anything not actually an amenity —
# not an error, just an empty list, which looks like "no results" rather
# than "wrong tag", making it an easy bug to miss. CATEGORY_TAGS is the
# single place that maps a friendly category name to its real OSM key.
# ---------------------------------------------------------------------------

CATEGORY_TAGS: dict[str, tuple[str, str]] = {
    "restaurant": ("amenity", "restaurant"),
    "fast_food": ("amenity", "fast_food"),
    "cafe": ("amenity", "cafe"),
    "bar": ("amenity", "bar"),
    "hospital": ("amenity", "hospital"),
    "pharmacy": ("amenity", "pharmacy"),
    "bank": ("amenity", "bank"),
    "atm": ("amenity", "atm"),
    "fuel": ("amenity", "fuel"),
    "school": ("amenity", "school"),
    "cinema": ("amenity", "cinema"),
    "nightclub": ("amenity", "nightclub"),
    "hotel": ("tourism", "hotel"),
    "guest_house": ("tourism", "guest_house"),
    "airport": ("aeroway", "aerodrome"),
    "supermarket": ("shop", "supermarket"),
    "market": ("amenity", "marketplace"),
}


def _fetch_overpass_pois(category: str, lat: float, lon: float, radius_m: int) -> list[dict]:
    tag_key, tag_value = CATEGORY_TAGS[category]
    query = f"""
    [out:json][timeout:25];
    (
      node["{tag_key}"="{tag_value}"](around:{radius_m},{lat},{lon});
      way["{tag_key}"="{tag_value}"](around:{radius_m},{lat},{lon});
    );
    out center body;
    """
    resp = httpx.post(settings.OVERPASS_BASE_URL, data={"data": query}, timeout=30)
    resp.raise_for_status()
    results = []
    for el in resp.json().get("elements", []):
        # Nodes have lat/lon directly; ways (buildings, areas) need "out center"
        # to get a representative point instead — handled by the query above.
        lat_val = el.get("lat") or el.get("center", {}).get("lat")
        lon_val = el.get("lon") or el.get("center", {}).get("lon")
        if lat_val is None or lon_val is None:
            continue
        tags = el.get("tags", {})
        results.append({
            "name": tags.get("name", "Unnamed"),
            "latitude": lat_val,
            "longitude": lon_val,
            "category": category,
            "address": ", ".join(filter(None, [tags.get("addr:street"), tags.get("addr:city")])) or None,
            "phone": tags.get("phone") or tags.get("contact:phone"),
            "opening_hours": tags.get("opening_hours"),
        })
    return results


def search_pois(category: str, lat: float, lon: float, radius_m: int = 5000) -> tuple[list[dict], bool]:
    if category not in CATEGORY_TAGS:
        raise ValueError(f"Unknown category '{category}'. Valid: {', '.join(CATEGORY_TAGS)}")
    return get_or_fetch("overpass_poi", _fetch_overpass_pois, category=category, lat=lat, lon=lon, radius_m=radius_m)


# ---------------------------------------------------------------------------
# Wikipedia — short description + photo for "click a place, see details"
# (used for live/OSM results, which have no curated description of their
# own — curated destinations already have one in data/destinations.json)
# ---------------------------------------------------------------------------

def _fetch_wikipedia_summary(title: str, lang: str) -> dict | None:
    resp = httpx.get(
        f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{title}",
        headers={"User-Agent": settings.GEO_USER_AGENT},
        timeout=10,
    )
    if resp.status_code == 404:
        return None  # no matching article — not an error, just nothing to show
    resp.raise_for_status()
    data = resp.json()
    if data.get("type") == "disambiguation":
        return None
    return {
        "title": data.get("title"),
        "extract": data.get("extract"),
        "image_url": (data.get("thumbnail") or {}).get("source"),
        "wikipedia_url": (data.get("content_urls", {}).get("desktop") or {}).get("page"),
    }


def get_place_summary(name: str, lang: str = "en") -> tuple[dict | None, bool]:
    lang = lang if lang in ("en", "fr") else "en"
    return get_or_fetch("wikipedia_summary", _fetch_wikipedia_summary, title=name, lang=lang)
