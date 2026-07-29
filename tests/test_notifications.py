from app import storage
from app.notifications import outbox


def _register(client, username, password="s3cr3t12"):
    return client.post(
        "/auth/register",
        json={"username": username, "email": f"{username}@example.com", "password": password, "preferences": []},
    )


def _verify(client, username):
    message = outbox.get_last_message_to(f"{username}@example.com")
    token = message["body"].split("token: ")[1].split("\n")[0]
    return client.post("/auth/verify", json={"token": token})


def _register_verify_login(client, username, password="s3cr3t12"):
    _register(client, username, password)
    _verify(client, username)
    resp = client.post("/auth/login", json={"username": username, "password": password})
    return resp.json()["access_token"]


def _auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def _make_admin(username):
    users = storage.read_all(storage.USERS_FILE)
    for u in users:
        if u["username"] == username:
            u["is_admin"] = True
    storage.replace_all(storage.USERS_FILE, users)


# ---------------------------------------------------------------------------
# Basic list / unread-count
# ---------------------------------------------------------------------------

def test_new_user_has_no_notifications(client):
    token = _register_verify_login(client, "quiet_user")
    resp = client.get("/notifications", headers=_auth_headers(token))
    assert resp.status_code == 200
    assert resp.json() == []
    assert client.get("/notifications/unread-count", headers=_auth_headers(token)).json()["unread_count"] == 0


# ---------------------------------------------------------------------------
# Admin send
# ---------------------------------------------------------------------------

def test_admin_send_to_specific_user(client):
    admin_token = _register_verify_login(client, "admin_notifier")
    _make_admin("admin_notifier")
    user_token = _register_verify_login(client, "target_user")

    resp = client.post(
        "/admin/notifications/send",
        json={"usernames": ["target_user"], "title": "Welcome", "message": "Thanks for joining GT!"},
        headers=_auth_headers(admin_token),
    )
    assert resp.status_code == 201
    assert resp.json()["notified"] == 1

    inbox = client.get("/notifications", headers=_auth_headers(user_token)).json()
    assert len(inbox) == 1
    assert inbox[0]["title"] == "Welcome"
    assert inbox[0]["is_read"] is False
    assert inbox[0]["sent_by"] == "admin_notifier"


def test_admin_broadcast_reaches_everyone(client):
    admin_token = _register_verify_login(client, "admin_broadcaster")
    _make_admin("admin_broadcaster")
    user_a = _register_verify_login(client, "bcast_a")
    user_b = _register_verify_login(client, "bcast_b")

    resp = client.post(
        "/admin/notifications/send",
        json={"broadcast": True, "title": "Maintenance notice", "message": "GT will be briefly offline tonight."},
        headers=_auth_headers(admin_token),
    )
    assert resp.status_code == 201
    # 3 users exist: the admin, bcast_a, bcast_b
    assert resp.json()["notified"] == 3

    assert len(client.get("/notifications", headers=_auth_headers(user_a)).json()) == 1
    assert len(client.get("/notifications", headers=_auth_headers(user_b)).json()) == 1


def test_admin_send_also_emails_when_requested(client):
    admin_token = _register_verify_login(client, "admin_emailer")
    _make_admin("admin_emailer")
    _register_verify_login(client, "email_target")

    resp = client.post(
        "/admin/notifications/send",
        json={"usernames": ["email_target"], "title": "Important", "message": "Please read this.", "also_email": True},
        headers=_auth_headers(admin_token),
    )
    assert resp.json()["emailed"] == 1
    sent = outbox.get_last_message_to("email_target@example.com")
    assert sent["subject"] == "Important"


def test_admin_send_unknown_username_rejected(client):
    admin_token = _register_verify_login(client, "admin_strict")
    _make_admin("admin_strict")
    resp = client.post(
        "/admin/notifications/send",
        json={"usernames": ["nobody_here"], "title": "x", "message": "y"},
        headers=_auth_headers(admin_token),
    )
    assert resp.status_code == 404


def test_non_admin_cannot_send_notifications(client):
    token = _register_verify_login(client, "regular_sender")
    resp = client.post(
        "/admin/notifications/send",
        json={"usernames": ["regular_sender"], "title": "x", "message": "y"},
        headers=_auth_headers(token),
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Mark as read / delete (1, some, all)
# ---------------------------------------------------------------------------

def _send_three(client, admin_token, username):
    for i in range(3):
        client.post(
            "/admin/notifications/send",
            json={"usernames": [username], "title": f"Note {i}", "message": "hi"},
            headers=_auth_headers(admin_token),
        )


def test_mark_specific_ids_as_read(client):
    admin_token = _register_verify_login(client, "admin_mark1")
    _make_admin("admin_mark1")
    user_token = _register_verify_login(client, "reader1")
    _send_three(client, admin_token, "reader1")

    inbox = client.get("/notifications", headers=_auth_headers(user_token)).json()
    first_id = inbox[0]["id"]

    resp = client.post("/notifications/mark-read", json={"ids": [first_id]}, headers=_auth_headers(user_token))
    assert resp.json()["marked_read"] == 1

    updated = client.get("/notifications", headers=_auth_headers(user_token)).json()
    read_map = {n["id"]: n["is_read"] for n in updated}
    assert read_map[first_id] is True
    assert sum(1 for v in read_map.values() if v) == 1


def test_mark_all_as_read(client):
    admin_token = _register_verify_login(client, "admin_mark2")
    _make_admin("admin_mark2")
    user_token = _register_verify_login(client, "reader2")
    _send_three(client, admin_token, "reader2")

    resp = client.post("/notifications/mark-read", json={"all": True}, headers=_auth_headers(user_token))
    assert resp.json()["marked_read"] == 3
    assert client.get("/notifications/unread-count", headers=_auth_headers(user_token)).json()["unread_count"] == 0


def test_delete_single_notification(client):
    admin_token = _register_verify_login(client, "admin_del1")
    _make_admin("admin_del1")
    user_token = _register_verify_login(client, "deleter1")
    _send_three(client, admin_token, "deleter1")

    inbox = client.get("/notifications", headers=_auth_headers(user_token)).json()
    target_id = inbox[0]["id"]

    resp = client.delete(f"/notifications/{target_id}", headers=_auth_headers(user_token))
    assert resp.status_code == 200

    remaining = client.get("/notifications", headers=_auth_headers(user_token)).json()
    assert len(remaining) == 2
    assert target_id not in {n["id"] for n in remaining}


def test_delete_some_notifications(client):
    admin_token = _register_verify_login(client, "admin_del2")
    _make_admin("admin_del2")
    user_token = _register_verify_login(client, "deleter2")
    _send_three(client, admin_token, "deleter2")

    inbox = client.get("/notifications", headers=_auth_headers(user_token)).json()
    ids_to_delete = [inbox[0]["id"], inbox[1]["id"]]

    resp = client.post("/notifications/delete", json={"ids": ids_to_delete}, headers=_auth_headers(user_token))
    assert resp.json()["deleted"] == 2

    remaining = client.get("/notifications", headers=_auth_headers(user_token)).json()
    assert len(remaining) == 1


def test_delete_all_notifications(client):
    admin_token = _register_verify_login(client, "admin_del3")
    _make_admin("admin_del3")
    user_token = _register_verify_login(client, "deleter3")
    _send_three(client, admin_token, "deleter3")

    resp = client.post("/notifications/delete", json={"all": True}, headers=_auth_headers(user_token))
    assert resp.json()["deleted"] == 3
    assert client.get("/notifications", headers=_auth_headers(user_token)).json() == []


def test_cannot_delete_or_read_someone_elses_notification(client):
    admin_token = _register_verify_login(client, "admin_iso")
    _make_admin("admin_iso")
    victim_token = _register_verify_login(client, "victim_user")
    attacker_token = _register_verify_login(client, "attacker_user")
    _send_three(client, admin_token, "victim_user")

    victim_inbox = client.get("/notifications", headers=_auth_headers(victim_token)).json()
    victim_notification_id = victim_inbox[0]["id"]

    # Attacker tries to delete victim's notification directly.
    resp = client.delete(f"/notifications/{victim_notification_id}", headers=_auth_headers(attacker_token))
    assert resp.status_code == 403

    # Attacker tries the bulk endpoint with victim's ID — should silently
    # affect zero of the attacker's own notifications (which don't include it).
    resp2 = client.post("/notifications/delete", json={"ids": [victim_notification_id]}, headers=_auth_headers(attacker_token))
    assert resp2.json()["deleted"] == 0

    # Victim's notification survives both attempts.
    still_there = client.get("/notifications", headers=_auth_headers(victim_token)).json()
    assert victim_notification_id in {n["id"] for n in still_there}


# ---------------------------------------------------------------------------
# Automatic notifications from other features
# ---------------------------------------------------------------------------

def test_referral_credit_creates_a_notification(client):
    sponsor_token = _register_verify_login(client, "notif_sponsor")
    sponsor_code = client.get("/users/me", headers=_auth_headers(sponsor_token)).json()["referral_code"]

    client.post(
        "/auth/register",
        json={"username": "notif_referred", "email": "notif_referred@example.com", "password": "s3cr3t12", "referral_code": sponsor_code},
    )
    _verify(client, "notif_referred")

    inbox = client.get("/notifications", headers=_auth_headers(sponsor_token)).json()
    assert any(n["category"] == "referral" for n in inbox)


def test_place_approval_creates_a_notification(client):
    admin_token = _register_verify_login(client, "admin_places_notif")
    _make_admin("admin_places_notif")
    submitter_token = _register_verify_login(client, "place_submitter")

    submit_resp = client.post(
        "/places",
        json={
            "name": "Notif Falls", "region": "West", "tags": ["waterfall"],
            "description": "A lovely quiet waterfall worth the short hike out to see.",
            "image_url": "https://example.com/f.jpg", "latitude": 5.5, "longitude": 10.5,
        },
        headers=_auth_headers(submitter_token),
    )
    place_id = submit_resp.json()["id"]

    client.post(f"/places/{place_id}/approve", headers=_auth_headers(admin_token))

    inbox = client.get("/notifications", headers=_auth_headers(submitter_token)).json()
    assert any(n["category"] == "place" and "approved" in n["title"].lower() for n in inbox)
