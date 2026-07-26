def _register_and_login(client, preferences):
    client.post(
        "/auth/register",
        json={"username": "bob", "email": "bob@example.com", "password": "s3cr3t12", "preferences": preferences},
    )
    resp = client.post("/auth/login", json={"username": "bob", "password": "s3cr3t12"})
    return resp.json()["access_token"]


def test_search_destinations_no_filters(client):
    resp = client.get("/destinations")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_search_destinations_by_tag(client):
    resp = client.get("/destinations", params={"tag": "beach"})
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp_no_match = client.get("/destinations", params={"tag": "skiing"})
    assert resp_no_match.json() == []


def test_recommendations_require_auth(client):
    resp = client.get("/recommendations")
    assert resp.status_code == 401


def test_recommendations_matches_preferences(client):
    token = _register_and_login(client, preferences=["beach"])
    resp = client.get("/recommendations", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 1
    assert "beach" in results[0]["tags"]


def test_recommendations_cold_start_returns_catalogue(client):
    token = _register_and_login(client, preferences=[])
    resp = client.get("/recommendations", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert len(resp.json()) == 1
