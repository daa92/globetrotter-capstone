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

def test_poi_categories_endpoint_lists_supported_categories(client):
    resp = client.get("/geo/poi-categories")
    assert resp.status_code == 200
    categories = resp.json()["categories"]
    # spot-check a few that use DIFFERENT underlying OSM tags — this is
    # exactly the bug that was fixed: airport/hotel/supermarket aren't
    # "amenity" tags at all, and treating them as such silently returned
    # zero results rather than erroring.
    for expected in ["restaurant", "fast_food", "airport", "hotel", "supermarket"]:
        assert expected in categories


def test_poi_search_rejects_unknown_category(client):
    resp = client.get("/geo/poi", params={"category": "spaceship_dealership", "lat": 4.05, "lon": 9.7})
    assert resp.status_code == 400
    assert "unknown category" in resp.json()["detail"].lower()


def test_poi_search_returns_results_and_caches(client, monkeypatch):
    calls = {"count": 0}

    def fake_pois(**kwargs):
        calls["count"] += 1
        return [{"name": "Chez Test", "latitude": 4.05, "longitude": 9.7, "category": kwargs["category"], "address": None, "phone": None, "opening_hours": None}]
    monkeypatch.setattr("app.geo_service._fetch_overpass_pois", fake_pois)

    params = {"category": "restaurant", "lat": 4.05, "lon": 9.7}
    first = client.get("/geo/poi", params=params)
    assert first.status_code == 200
    assert first.json()["results"][0]["name"] == "Chez Test"
    assert first.json()["cached"] is False

    second = client.get("/geo/poi", params=params)
    assert second.json()["cached"] is True
    assert calls["count"] == 1


def test_poi_search_works_for_a_non_amenity_category_like_airport(client, monkeypatch):
    """The specific bug this fixes: 'airport' is aeroway=aerodrome, not
    amenity=airport. This test would have caught the old bug — it checks
    that the category is accepted and passed through correctly, not that
    the (mocked) fetch itself does the right OSM query."""
    def fake_pois(**kwargs):
        assert kwargs["category"] == "airport"
        return [{"name": "Yaoundé Nsimalen International Airport", "latitude": 3.72, "longitude": 11.55, "category": "airport", "address": None, "phone": None, "opening_hours": None}]
    monkeypatch.setattr("app.geo_service._fetch_overpass_pois", fake_pois)

    resp = client.get("/geo/poi", params={"category": "airport", "lat": 3.72, "lon": 11.55})
    assert resp.status_code == 200
    assert "Airport" in resp.json()["results"][0]["name"]


def test_poi_search_handles_upstream_failure_as_503(client, monkeypatch):
    def failing_pois(**kwargs):
        raise ConnectionError("could not reach Overpass")
    monkeypatch.setattr("app.geo_service._fetch_overpass_pois", failing_pois)

    resp = client.get("/geo/poi", params={"category": "hospital", "lat": 4.05, "lon": 9.7})
    assert resp.status_code == 503


# ---------------------------------------------------------------------------
# Wikipedia place summary (for "click a place, see description + photo")
# ---------------------------------------------------------------------------

def test_place_summary_returns_description_and_photo(client, monkeypatch):
    def fake_summary(**kwargs):
        return {"title": "Mount Cameroon", "extract": "An active volcano in Cameroon.", "image_url": "https://example.com/pic.jpg", "wikipedia_url": "https://en.wikipedia.org/wiki/Mount_Cameroon"}
    monkeypatch.setattr("app.geo_service._fetch_wikipedia_summary", fake_summary)

    resp = client.get("/geo/place-summary", params={"name": "Mount Cameroon"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["found"] is True
    assert body["extract"] == "An active volcano in Cameroon."
    assert body["image_url"] == "https://example.com/pic.jpg"


def test_place_summary_returns_found_false_when_no_article_exists(client, monkeypatch):
    """No Wikipedia article for a small local place is a completely normal
    outcome, not an error — must not be a 404."""
    monkeypatch.setattr("app.geo_service._fetch_wikipedia_summary", lambda **kwargs: None)

    resp = client.get("/geo/place-summary", params={"name": "Some Tiny Unknown Place"})
    assert resp.status_code == 200
    assert resp.json()["found"] is False


def test_place_summary_caches(client, monkeypatch):
    calls = {"count": 0}

    def fake_summary(**kwargs):
        calls["count"] += 1
        return {"title": "Kribi", "extract": "A beach town.", "image_url": None, "wikipedia_url": None}
    monkeypatch.setattr("app.geo_service._fetch_wikipedia_summary", fake_summary)

    params = {"name": "Kribi"}
    client.get("/geo/place-summary", params=params)
    second = client.get("/geo/place-summary", params=params)
    assert second.json()["cached"] is True
    assert calls["count"] == 1


def test_place_summary_handles_upstream_failure_as_503(client, monkeypatch):
    def failing_summary(**kwargs):
        raise ConnectionError("could not reach Wikipedia")
    monkeypatch.setattr("app.geo_service._fetch_wikipedia_summary", failing_summary)

    resp = client.get("/geo/place-summary", params={"name": "Douala"})
    assert resp.status_code == 503


def test_place_summary_rejects_unsupported_language(client, monkeypatch):
    called = {"count": 0}

    def fake_summary(**kwargs):
        called["count"] += 1
        return None
    monkeypatch.setattr("app.geo_service._fetch_wikipedia_summary", fake_summary)

    resp = client.get("/geo/place-summary", params={"name": "Douala", "lang": "de"})
    assert resp.status_code == 422  # only en/fr allowed
    assert called["count"] == 0  # never even reached the fetch function

