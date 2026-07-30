from datetime import datetime, timedelta, timezone

from app import storage
from app.notifications import outbox


def _verify_via_outbox(client, to_address):
    message = outbox.get_last_message_to(to_address)
    token = message["body"].split("code: ")[-1].split("token: ")[-1].split("\n")[0].strip()
    return client.post("/auth/verify", json={"token": token})


def _register_phone(client, username, phone, password="s3cr3t12"):
    return client.post(
        "/auth/register/phone",
        json={"username": username, "phone": phone, "password": password, "preferences": []},
    )


def _register_email_and_verify(client, username, password="s3cr3t12"):
    client.post("/auth/register", json={"username": username, "email": f"{username}@example.com", "password": password, "preferences": []})
    _verify_via_outbox(client, f"{username}@example.com")


# ---------------------------------------------------------------------------
# Phone registration
# ---------------------------------------------------------------------------

def test_phone_registration_sends_sms_and_verifies(client):
    resp = _register_phone(client, "phone_user", "+237650000001")
    assert resp.status_code == 201
    body = resp.json()
    assert body["phone"] == "+237650000001"
    assert body["email"] is None

    message = outbox.get_last_message_to("+237650000001")
    assert message["channel"] == "sms"

    verify_resp = _verify_via_outbox(client, "+237650000001")
    assert verify_resp.status_code == 200

    login = client.post("/auth/login", json={"username": "phone_user", "password": "s3cr3t12"})
    assert login.status_code == 200
    assert "access_token" in login.json()


def test_phone_registration_rejects_duplicate_phone(client):
    _register_phone(client, "phone_a", "+237650000002")
    resp = _register_phone(client, "phone_b", "+237650000002")
    assert resp.status_code == 409


def test_phone_registration_unverified_account_still_gets_cleaned_up(client):
    from app.cleanup import purge_unverified_users

    _register_phone(client, "stale_phone_user", "+237650000003")
    users = storage.read_all(storage.USERS_FILE)
    for u in users:
        if u["username"] == "stale_phone_user":
            u["created_at"] = (datetime.now(timezone.utc) - timedelta(minutes=31)).isoformat()
    storage.replace_all(storage.USERS_FILE, users)

    deleted = purge_unverified_users()
    assert deleted == ["stale_phone_user"]


def test_invalid_phone_format_rejected(client):
    resp = client.post(
        "/auth/register/phone",
        json={"username": "bad_phone", "phone": "not-a-number", "password": "s3cr3t12"},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Password recovery
# ---------------------------------------------------------------------------

def test_password_reset_request_is_generic_for_unknown_username(client):
    resp = client.post("/auth/password-reset/request", json={"username": "nobody_at_all"})
    assert resp.status_code == 200
    assert "if that account exists" in resp.json()["detail"].lower()


def test_password_reset_request_is_generic_for_known_username_too(client):
    _register_email_and_verify(client, "reset_target")
    resp = client.post("/auth/password-reset/request", json={"username": "reset_target"})
    assert resp.status_code == 200
    assert "if that account exists" in resp.json()["detail"].lower()
    # Same wording either way — can't distinguish existence from the response alone.


def test_password_reset_full_flow_for_email_account(client):
    _register_email_and_verify(client, "email_reset_user")
    client.post("/auth/password-reset/request", json={"username": "email_reset_user"})

    message = outbox.get_last_message_to("email_reset_user@example.com")
    token = message["body"].split(": ")[-1]

    confirm = client.post("/auth/password-reset/confirm", json={"token": token, "new_password": "NewPass123"})
    assert confirm.status_code == 200

    old_login = client.post("/auth/login", json={"username": "email_reset_user", "password": "s3cr3t12"})
    assert old_login.status_code == 401

    new_login = client.post("/auth/login", json={"username": "email_reset_user", "password": "NewPass123"})
    assert new_login.status_code == 200


def test_password_reset_full_flow_for_phone_account(client):
    _register_phone(client, "phone_reset_user", "+237650000004")
    _verify_via_outbox(client, "+237650000004")

    client.post("/auth/password-reset/request", json={"username": "phone_reset_user"})
    message = outbox.get_last_message_to("+237650000004")
    assert message["channel"] == "sms"
    token = message["body"].split(": ")[-1]

    confirm = client.post("/auth/password-reset/confirm", json={"token": token, "new_password": "NewPass456"})
    assert confirm.status_code == 200

    new_login = client.post("/auth/login", json={"username": "phone_reset_user", "password": "NewPass456"})
    assert new_login.status_code == 200


def test_password_reset_confirm_rejects_invalid_token(client):
    resp = client.post("/auth/password-reset/confirm", json={"token": "not-a-real-token", "new_password": "NewPass123"})
    assert resp.status_code == 400


def test_password_reset_confirm_rejects_expired_token(client):
    _register_email_and_verify(client, "expired_reset_user")
    client.post("/auth/password-reset/request", json={"username": "expired_reset_user"})

    # Backdate the token's expiry so it's already expired.
    users = storage.read_all(storage.USERS_FILE)
    for u in users:
        if u["username"] == "expired_reset_user":
            u["password_reset_expires_at"] = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
            token = u["password_reset_token"]
    storage.replace_all(storage.USERS_FILE, users)

    resp = client.post("/auth/password-reset/confirm", json={"token": token, "new_password": "NewPass123"})
    assert resp.status_code == 400
    assert "expired" in resp.json()["detail"].lower()


def test_password_reset_creates_a_security_notification(client):
    _register_email_and_verify(client, "notif_reset_user")
    client.post("/auth/password-reset/request", json={"username": "notif_reset_user"})
    message = outbox.get_last_message_to("notif_reset_user@example.com")
    token = message["body"].split(": ")[-1]
    client.post("/auth/password-reset/confirm", json={"token": token, "new_password": "NewPass123"})

    login = client.post("/auth/login", json={"username": "notif_reset_user", "password": "NewPass123"})
    access_token = login.json()["access_token"]

    inbox = client.get("/notifications", headers={"Authorization": f"Bearer {access_token}"}).json()
    assert any(n["category"] == "security" for n in inbox)


def test_google_only_account_can_use_password_reset_to_set_a_local_password(client, monkeypatch):
    monkeypatch.setattr("app.config.settings.GOOGLE_CLIENT_ID", "fake-client-id.apps.googleusercontent.com")
    monkeypatch.setattr(
        "app.routers.auth.verify_google_id_token",
        lambda token: {"email": "googleonly2@gmail.com", "sub": "sub-1", "email_verified": True, "picture": None},
    )
    client.post("/auth/google", json={"id_token": "fake-token"})

    # No local password yet — this account can still go through password reset
    # to set one for the first time, rather than being locked out of it.
    client.post("/auth/password-reset/request", json={"username": "googleonly2"})
    message = outbox.get_last_message_to("googleonly2@gmail.com")
    token = message["body"].split(": ")[-1]

    confirm = client.post("/auth/password-reset/confirm", json={"token": token, "new_password": "FirstPass123"})
    assert confirm.status_code == 200

    login = client.post("/auth/login", json={"username": "googleonly2", "password": "FirstPass123"})
    assert login.status_code == 200
