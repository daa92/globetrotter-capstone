"""
tests/test_google_auth.py

Real Google ID token verification requires a live call to Google's
certificate endpoint — a test suite should never depend on that. Every
test here monkeypatches verify_google_id_token where it's *used*
(app.routers.auth), returning a controlled fake decoded payload, so we're
testing GT's account-linking/creation logic in isolation from Google's
actual servers.
"""
from app import storage
from app.notifications import outbox


def _fake_google_payload(email, sub="google-sub-123", email_verified=True, picture="https://example.com/pic.jpg"):
    return {"email": email, "sub": sub, "email_verified": email_verified, "picture": picture, "name": "Test User"}


def _patch_google(monkeypatch, payload):
    monkeypatch.setattr("app.routers.auth.verify_google_id_token", lambda token: payload)


def _register_and_verify(client, username, password="s3cr3t12"):
    client.post("/auth/register", json={"username": username, "email": f"{username}@example.com", "password": password, "preferences": []})
    message = outbox.get_last_message_to(f"{username}@example.com")
    token = message["body"].split("token: ")[1].split("\n")[0]
    client.post("/auth/verify", json={"token": token})


def test_google_signin_requires_client_id_configured(client, monkeypatch):
    monkeypatch.setattr("app.config.settings.GOOGLE_CLIENT_ID", "")
    resp = client.post("/auth/google", json={"id_token": "whatever"})
    assert resp.status_code == 501


def test_google_signin_creates_new_verified_account(client, monkeypatch):
    monkeypatch.setattr("app.config.settings.GOOGLE_CLIENT_ID", "fake-client-id.apps.googleusercontent.com")
    _patch_google(monkeypatch, _fake_google_payload("newperson@gmail.com"))

    resp = client.post("/auth/google", json={"id_token": "fake-token"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()

    token = resp.json()["access_token"]
    me = client.get("/users/me", headers={"Authorization": f"Bearer {token}"}).json()
    assert me["email"] == "newperson@gmail.com"
    assert me["is_verified"] is True  # Google already confirmed the email
    assert me["profile_picture_url"] == "https://example.com/pic.jpg"
    assert me["username"] == "newperson"  # derived from the email's local part


def test_google_signin_rejects_unverified_google_email(client, monkeypatch):
    monkeypatch.setattr("app.config.settings.GOOGLE_CLIENT_ID", "fake-client-id.apps.googleusercontent.com")
    _patch_google(monkeypatch, _fake_google_payload("sketchy@gmail.com", email_verified=False))

    resp = client.post("/auth/google", json={"id_token": "fake-token"})
    assert resp.status_code == 400


def test_google_signin_rejects_invalid_token(client, monkeypatch):
    monkeypatch.setattr("app.config.settings.GOOGLE_CLIENT_ID", "fake-client-id.apps.googleusercontent.com")

    def _raise(token):
        raise ValueError("Token expired")
    monkeypatch.setattr("app.routers.auth.verify_google_id_token", _raise)

    resp = client.post("/auth/google", json={"id_token": "expired-token"})
    assert resp.status_code == 401


def test_google_signin_network_failure_returns_503_not_500(client, monkeypatch):
    """A transport failure reaching Google (cert endpoint down, DNS hiccup,
    etc.) is a different failure mode than an invalid token — verified this
    actually happens by calling the real (network-blocked, in this sandbox)
    verifier once and confirming it raises GoogleAuthError, not ValueError."""
    from google.auth.exceptions import TransportError

    monkeypatch.setattr("app.config.settings.GOOGLE_CLIENT_ID", "fake-client-id.apps.googleusercontent.com")

    def _raise(token):
        raise TransportError("Could not fetch certificates")
    monkeypatch.setattr("app.routers.auth.verify_google_id_token", _raise)

    resp = client.post("/auth/google", json={"id_token": "whatever"})
    assert resp.status_code == 503


def test_google_signin_links_to_existing_local_account_by_email(client, monkeypatch):
    _register_and_verify(client, "existing_local")  # email: existing_local@example.com

    monkeypatch.setattr("app.config.settings.GOOGLE_CLIENT_ID", "fake-client-id.apps.googleusercontent.com")
    _patch_google(monkeypatch, _fake_google_payload("existing_local@example.com"))

    resp = client.post("/auth/google", json={"id_token": "fake-token"})
    assert resp.status_code == 200

    token = resp.json()["access_token"]
    me = client.get("/users/me", headers={"Authorization": f"Bearer {token}"}).json()
    assert me["username"] == "existing_local"  # logged into the SAME account, not a duplicate

    all_users = storage.read_all(storage.USERS_FILE)
    matching = [u for u in all_users if u["email"] == "existing_local@example.com"]
    assert len(matching) == 1  # no duplicate account was created


def test_username_collision_gets_a_numeric_suffix(client, monkeypatch):
    _register_and_verify(client, "popular")  # takes the username "popular"

    monkeypatch.setattr("app.config.settings.GOOGLE_CLIENT_ID", "fake-client-id.apps.googleusercontent.com")
    _patch_google(monkeypatch, _fake_google_payload("popular@gmail.com"))  # different email, same local part

    resp = client.post("/auth/google", json={"id_token": "fake-token"})
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    me = client.get("/users/me", headers={"Authorization": f"Bearer {token}"}).json()
    assert me["username"] == "popular1"


def test_password_login_blocked_for_google_only_account(client, monkeypatch):
    monkeypatch.setattr("app.config.settings.GOOGLE_CLIENT_ID", "fake-client-id.apps.googleusercontent.com")
    _patch_google(monkeypatch, _fake_google_payload("googleonly@gmail.com"))
    client.post("/auth/google", json={"id_token": "fake-token"})

    resp = client.post("/auth/login", json={"username": "googleonly", "password": "anything-at-all1"})
    assert resp.status_code == 401  # generic invalid-credentials, not a crash


def test_google_signin_respects_existing_mfa(client, monkeypatch):
    import pyotp

    _register_and_verify(client, "mfa_google_user")
    login_resp = client.post("/auth/login", json={"username": "mfa_google_user", "password": "s3cr3t12"})
    access_token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    setup = client.post("/auth/mfa/setup", headers=headers).json()
    code = pyotp.TOTP(setup["secret"]).now()
    client.post("/auth/mfa/confirm", json={"code": code}, headers=headers)

    monkeypatch.setattr("app.config.settings.GOOGLE_CLIENT_ID", "fake-client-id.apps.googleusercontent.com")
    _patch_google(monkeypatch, _fake_google_payload("mfa_google_user@example.com"))

    challenge = client.post("/auth/google", json={"id_token": "fake-token"})
    assert challenge.json().get("mfa_required") is True

    fresh_code = pyotp.TOTP(setup["secret"]).now()
    full = client.post("/auth/google", json={"id_token": "fake-token", "mfa_code": fresh_code})
    assert full.status_code == 200
    assert "access_token" in full.json()
