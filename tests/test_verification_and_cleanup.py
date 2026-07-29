from datetime import datetime, timedelta, timezone

from app import storage
from app.cleanup import purge_unverified_users
from app.notifications import outbox


def _register(client, username="bob", password="s3cr3t12"):
    return client.post(
        "/auth/register",
        json={"username": username, "email": f"{username}@example.com", "password": password, "preferences": []},
    )


def test_unverified_account_cannot_log_in(client):
    _register(client)
    resp = client.post("/auth/login", json={"username": "bob", "password": "s3cr3t12"})
    assert resp.status_code == 403
    assert "not yet verified" in resp.json()["detail"].lower()


def test_verification_token_is_sent_via_outbox(client):
    _register(client)
    message = outbox.get_last_message_to("bob@example.com")
    assert message is not None
    assert message["channel"] == "email"
    assert "token" in message["body"].lower()


def test_verify_with_valid_token_enables_login(client):
    _register(client)
    message = outbox.get_last_message_to("bob@example.com")
    token = message["body"].split("token: ")[1].split("\n")[0]

    verify_resp = client.post("/auth/verify", json={"token": token})
    assert verify_resp.status_code == 200

    login_resp = client.post("/auth/login", json={"username": "bob", "password": "s3cr3t12"})
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.json()


def test_verify_with_invalid_token_rejected(client):
    _register(client)
    resp = client.post("/auth/verify", json={"token": "not-a-real-token"})
    assert resp.status_code == 400


def test_verify_twice_is_a_no_op_not_an_error(client):
    _register(client)
    message = outbox.get_last_message_to("bob@example.com")
    token = message["body"].split("token: ")[1].split("\n")[0]

    first = client.post("/auth/verify", json={"token": token})
    assert first.status_code == 200

    second = client.post("/auth/verify", json={"token": token})
    assert second.status_code == 200
    assert "already verified" in second.json()["detail"].lower()


def test_cleanup_purges_stale_unverified_accounts(client):
    _register(client, username="stale_user")
    _register(client, username="fresh_user")

    # Verify one of them — it must survive cleanup regardless of age.
    message = outbox.get_last_message_to("fresh_user@example.com")
    token = message["body"].split("token: ")[1].split("\n")[0]
    client.post("/auth/verify", json={"token": token})

    # Backdate only the unverified user's registration time past the TTL.
    users = storage.read_all(storage.USERS_FILE)
    for u in users:
        if u["username"] == "stale_user":
            u["created_at"] = (datetime.now(timezone.utc) - timedelta(minutes=31)).isoformat()
    storage.replace_all(storage.USERS_FILE, users)

    deleted = purge_unverified_users()
    assert deleted == ["stale_user"]

    remaining_usernames = {u["username"] for u in storage.read_all(storage.USERS_FILE)}
    assert "stale_user" not in remaining_usernames
    assert "fresh_user" in remaining_usernames


def test_cleanup_leaves_recently_registered_unverified_accounts_alone(client):
    _register(client, username="just_signed_up")
    deleted = purge_unverified_users()
    assert deleted == []
    remaining_usernames = {u["username"] for u in storage.read_all(storage.USERS_FILE)}
    assert "just_signed_up" in remaining_usernames
