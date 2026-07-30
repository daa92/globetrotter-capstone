"""
tests/test_geo.py

Real calls to Nominatim/Overpass/OpenRouteService need live internet
access to those specific services — a test suite should never depend on
that. Every test here monkeypatches the isolated _fetch_* functions in
app/geo_service.py, so what's actually under test is GT's caching behavior and
error handling, not the third-party services themselves.
"""
from datetime import datetime, timedelta, timezone

from app import storage


def _call_counter():
    calls = {"count": 0}

    def fake_fetch(**kwargs):
        calls["count"] += 1
        return [{"name": "Mock Place", "display_name": "Mock Place, Cameroon", "latitude": 4.05, "longitude": 9.7, "type": "city"}]

    return calls, fake_fetch


# ---------------------------------------------------------------------------
# Nominatim search + caching
# ---------------------------------------------------------------------------

def test_search_caches_after_first_call(client, monkeypatch):
    calls, fake_fetch = _call_counter()
    monkeypatch.setattr("app.geo_service._fetch_nominatim_search", fake_fetch)

    first = client.get("/geo/search", params={"q": "Douala"})
    assert first.status_code == 200
    assert first.json()["cached"] is False
    assert first.json()["results"][0]["name"] == "Mock Place"

    second = client.get("/geo/search", params={"q": "Douala"})
    assert second.json()["cached"] is True
    assert second.json()["results"] == first.json()["results"]

    assert calls["count"] == 1  # the live fetch only ran once, second call was served from cache


def test_search_different_queries_are_cached_separately(client, monkeypatch):
    calls, fake_fetch = _call_counter()
    monkeypatch.setattr("app.geo_service._fetch_nominatim_search", fake_fetch)

    client.get("/geo/search", params={"q": "Douala"})
    client.get("/geo/search", params={"q": "Yaounde"})
    assert calls["count"] == 2  # two distinct queries, two live fetches


def test_search_stale_cache_entry_triggers_a_refetch(client, monkeypatch):
    calls, fake_fetch = _call_counter()
    monkeypatch.setattr("app.geo_service._fetch_nominatim_search", fake_fetch)
    monkeypatch.setattr("app.config.settings.GEO_CACHE_TTL_HOURS", 168)

    client.get("/geo/search", params={"q": "Kribi"})
    assert calls["count"] == 1

    # Backdate the cache entry past the TTL.
    entries = storage.read_all(storage.GEO_CACHE_FILE)
    for e in entries:
        e["cached_at"] = (datetime.now(timezone.utc) - timedelta(hours=200)).isoformat()
    storage.replace_all(storage.GEO_CACHE_FILE, entries)

    client.get("/geo/search", params={"q": "Kribi"})
    assert calls["count"] == 2  # stale entry, so it fetched again


def test_search_rejects_too_short_query(client):
    resp = client.get("/geo/search", params={"q": "a"})
    assert resp.status_code == 422


def test_search_handles_upstream_failure_as_503_not_500(client, monkeypatch):
    """Caught this the hard way: originally /geo/search had no error
    handling at all around the live call, unlike /geo/route and /geo/poi.
    Discovered it by actually trying to reach Nominatim from this
    environment (blocked by the sandbox's own egress allowlist) and
    getting an unhandled 500 instead of a graceful failure."""
    def failing_search(**kwargs):
        raise ConnectionError("could not reach Nominatim")
    monkeypatch.setattr("app.geo_service._fetch_nominatim_search", failing_search)

    resp = client.get("/geo/search", params={"q": "Douala"})
    assert resp.status_code == 503


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------

def test_route_requires_api_key_configured(client, monkeypatch):
    monkeypatch.setattr("app.config.settings.OPENROUTESERVICE_API_KEY", "")
    resp = client.get("/geo/route", params={"from_lat": 4.05, "from_lng": 9.7, "to_lat": 4.06, "to_lng": 9.75})
    assert resp.status_code == 501


def test_route_returns_distance_and_duration_and_caches(client, monkeypatch):
    monkeypatch.setattr("app.config.settings.OPENROUTESERVICE_API_KEY", "fake-key")

    calls = {"count": 0}

    def fake_route(**kwargs):
        calls["count"] += 1
        return {"distance_km": 12.3, "duration_minutes": 150.0, "profile": kwargs["profile"]}

    monkeypatch.setattr("app.geo_service._fetch_route", fake_route)

    params = {"from_lat": 4.05, "from_lng": 9.7, "to_lat": 4.06, "to_lng": 9.75, "profile": "foot-walking"}
    first = client.get("/geo/route", params=params)
    assert first.status_code == 200
    assert first.json()["distance_km"] == 12.3
    assert first.json()["cached"] is False

    second = client.get("/geo/route", params=params)
    assert second.json()["cached"] is True
    assert calls["count"] == 1


def test_route_handles_upstream_failure_as_503(client, monkeypatch):
    monkeypatch.setattr("app.config.settings.OPENROUTESERVICE_API_KEY", "fake-key")

    def failing_route(**kwargs):
        raise ConnectionError("could not reach OpenRouteService")
    monkeypatch.setattr("app.geo_service._fetch_route", failing_route)

    resp = client.get("/geo/route", params={"from_lat": 4.05, "from_lng": 9.7, "to_lat": 4.06, "to_lng": 9.75})
    assert resp.status_code == 503


def test_route_rejects_invalid_profile(client, monkeypatch):
    monkeypatch.setattr("app.config.settings.OPENROUTESERVICE_API_KEY", "fake-key")
    resp = client.get(
        "/geo/route",
        params={"from_lat": 4.05, "from_lng": 9.7, "to_lat": 4.06, "to_lng": 9.75, "profile": "teleport"},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POI search
# ---------------------------------------------------------------------------

def test_poi_search_returns_results_and_caches(client, monkeypatch):
    calls = {"count": 0}

    def fake_pois(**kwargs):
        calls["count"] += 1
        return [{"name": "Chez Test", "latitude": 4.05, "longitude": 9.7, "amenity": kwargs["amenity"]}]
    monkeypatch.setattr("app.geo_service._fetch_overpass_pois", fake_pois)

    params = {"amenity": "restaurant", "lat": 4.05, "lon": 9.7}
    first = client.get("/geo/poi", params=params)
    assert first.status_code == 200
    assert first.json()["results"][0]["name"] == "Chez Test"
    assert first.json()["cached"] is False

    second = client.get("/geo/poi", params=params)
    assert second.json()["cached"] is True
    assert calls["count"] == 1


def test_poi_search_handles_upstream_failure_as_503(client, monkeypatch):
    def failing_pois(**kwargs):
        raise ConnectionError("could not reach Overpass")
    monkeypatch.setattr("app.geo_service._fetch_overpass_pois", failing_pois)

    resp = client.get("/geo/poi", params={"amenity": "hospital", "lat": 4.05, "lon": 9.7})
    assert resp.status_code == 503
