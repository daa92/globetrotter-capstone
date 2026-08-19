from app import storage
from app.config import settings
from app.notifications import outbox


def _register(client, username="alice", password="s3cr3t12"):
    return client.post(
        "/auth/register",
        json={"username": username, "email": f"{username}@example.com", "password": password, "preferences": ["beach"]},
    )


def _verify(client, email):
    """Pulls the verification token straight from the outbox (our stub email/SMS
    sender) and confirms it, the way clicking an email link would in production."""
    message = outbox.get_last_message_to(email)
    token = message["body"].split("token: ")[1].split("\n")[0]
    resp = client.post("/auth/verify", json={"token": token})
    assert resp.status_code == 200, resp.text
    return token


def _register_and_verify(client, username="alice", password="s3cr3t12"):
    _register(client, username, password)
    _verify(client, f"{username}@example.com")


def test_register_success(client):
    resp = _register(client)
    assert resp.status_code == 201
    body = resp.json()
    assert body["username"] == "alice"
    assert "hashed_password" not in body  # never leak the hash


def test_register_duplicate_username_rejected(client):
    _register(client)
    resp = _register(client)
    assert resp.status_code == 409


def test_login_wrong_password_rejected(client):
    _register_and_verify(client)
    resp = client.post("/auth/login", json={"username": "alice", "password": "wrong-pass1"})
    assert resp.status_code == 401


def test_login_success_returns_access_token_and_refresh_cookie(client):
    _register_and_verify(client)
    resp = client.post("/auth/login", json={"username": "alice", "password": "s3cr3t12"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()
    assert "gt_refresh_token" in resp.cookies


def test_refresh_cookie_is_samesite_none_when_secure(client, monkeypatch):
    """
    Regression test for the "visiting the admin page logs me out" bug.

    Frontend and backend live on different origins in production, so the
    refresh cookie is cross-site. SameSite=Lax cookies are NOT attached to
    cross-site fetch()/XHR calls (only top-level navigations), so a Lax
    cookie set in production silently fails to reach POST /auth/refresh on
    every full page load — which is exactly what happens on the admin
    route, since it's the one page reached by typing/bookmarking a URL
    instead of an in-app <Link>. Once COOKIE_SECURE is on (real HTTPS
    deploy), the cookie must be SameSite=None or session-restore-on-reload
    silently breaks everywhere, not just on that page.
    """
    monkeypatch.setattr(settings, "COOKIE_SECURE", True)
    _register_and_verify(client)
    resp = client.post("/auth/login", json={"username": "alice", "password": "s3cr3t12"})
    assert resp.status_code == 200
    set_cookie = resp.headers.get("set-cookie", "")
    assert "gt_refresh_token" in set_cookie
    assert "samesite=none" in set_cookie.lower()
    assert "secure" in set_cookie.lower()


def test_refresh_cookie_is_samesite_lax_when_not_secure(client, monkeypatch):
    """Local/plain-http dev (COOKIE_SECURE=False) keeps Lax — SameSite=None
    without Secure is rejected outright by browsers, and local dev doesn't
    need it since it isn't genuinely cross-site in the way that matters."""
    monkeypatch.setattr(settings, "COOKIE_SECURE", False)
    _register_and_verify(client)
    resp = client.post("/auth/login", json={"username": "alice", "password": "s3cr3t12"})
    assert resp.status_code == 200
    set_cookie = resp.headers.get("set-cookie", "")
    assert "samesite=lax" in set_cookie.lower()


def test_protected_route_requires_token(client):
    resp = client.get("/users/me")
    assert resp.status_code == 401


def test_protected_route_with_valid_token(client):
    _register_and_verify(client)
    login_resp = client.post("/auth/login", json={"username": "alice", "password": "s3cr3t12"})
    token = login_resp.json()["access_token"]
    resp = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["username"] == "alice"


def test_mfa_full_enrollment_and_login_flow(client):
    import pyotp

    _register_and_verify(client)
    login_resp = client.post("/auth/login", json={"username": "alice", "password": "s3cr3t12"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    setup_resp = client.post("/auth/mfa/setup", headers=headers)
    assert setup_resp.status_code == 200
    secret = setup_resp.json()["secret"]

    code = pyotp.TOTP(secret).now()
    confirm_resp = client.post("/auth/mfa/confirm", json={"code": code}, headers=headers)
    assert confirm_resp.status_code == 200

    # Login without MFA code now returns a challenge, not tokens.
    challenge_resp = client.post("/auth/login", json={"username": "alice", "password": "s3cr3t12"})
    assert challenge_resp.json().get("mfa_required") is True

    # Login with the correct TOTP code succeeds.
    fresh_code = pyotp.TOTP(secret).now()
    full_login = client.post(
        "/auth/login",
        json={"username": "alice", "password": "s3cr3t12", "mfa_code": fresh_code},
    )
    assert full_login.status_code == 200
    assert "access_token" in full_login.json()
