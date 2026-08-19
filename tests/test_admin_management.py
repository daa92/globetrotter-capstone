"""
tests/test_admin_management.py

Covers the principal-admin-only "manage other admins" surface:
  - only the principal admin can promote/revoke/re-permission admins
  - a regular admin (even with every individual permission) cannot
  - promoted admins are scoped to exactly the permissions they were given
  - the principal admin can never be revoked, including by themselves
  - the bootstrap endpoint only ever creates ONE principal admin
"""
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


def _make_principal(username):
    users = storage.read_all(storage.USERS_FILE)
    for u in users:
        if u["username"] == username:
            u["is_admin"] = True
            u["is_principal_admin"] = True
            u["admin_permissions"] = ["payouts", "places", "feedback", "notifications"]
    storage.replace_all(storage.USERS_FILE, users)


def test_principal_can_promote_user_with_specific_permissions(client):
    principal_token = _register_verify_login(client, "principal1")
    _make_principal("principal1")
    _register_verify_login(client, "future_admin")

    resp = client.post(
        "/admin/admins/future_admin/promote",
        json={"permissions": ["payouts", "feedback"]},
        headers=_auth_headers(principal_token),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["is_principal_admin"] is False
    assert sorted(body["admin_permissions"]) == ["feedback", "payouts"]

    users = storage.read_all(storage.USERS_FILE)
    target = next(u for u in users if u["username"] == "future_admin")
    assert target["is_admin"] is True


def test_promoted_admin_only_has_granted_permission(client):
    principal_token = _register_verify_login(client, "principal2")
    _make_principal("principal2")
    admin_token = _register_verify_login(client, "payouts_only_admin")
    client.post(
        "/admin/admins/payouts_only_admin/promote",
        json={"permissions": ["payouts"]},
        headers=_auth_headers(principal_token),
    )

    # Has the permission they were granted...
    resp = client.get("/admin/payouts", headers=_auth_headers(admin_token))
    assert resp.status_code == 200

    # ...but not one they weren't.
    resp = client.get("/places/pending", headers=_auth_headers(admin_token))
    assert resp.status_code == 403

    resp = client.get("/feedback", headers=_auth_headers(admin_token))
    assert resp.status_code == 403


def test_regular_admin_cannot_manage_other_admins(client):
    principal_token = _register_verify_login(client, "principal3")
    _make_principal("principal3")
    regular_admin_token = _register_verify_login(client, "regular_admin")
    client.post(
        "/admin/admins/regular_admin/promote",
        json={"permissions": ["payouts", "places", "feedback", "notifications"]},
        headers=_auth_headers(principal_token),
    )
    _register_verify_login(client, "bystander")

    # Even with every individual permission, a non-principal admin can't
    # promote/revoke/re-permission other admins.
    resp = client.post(
        "/admin/admins/bystander/promote",
        json={"permissions": []},
        headers=_auth_headers(regular_admin_token),
    )
    assert resp.status_code == 403

    resp = client.get("/admin/admins", headers=_auth_headers(regular_admin_token))
    assert resp.status_code == 403


def test_principal_can_update_and_revoke_admin_permissions(client):
    principal_token = _register_verify_login(client, "principal4")
    _make_principal("principal4")
    admin_token = _register_verify_login(client, "flexible_admin")
    client.post(
        "/admin/admins/flexible_admin/promote",
        json={"permissions": ["payouts"]},
        headers=_auth_headers(principal_token),
    )

    # Grant an additional privilege.
    resp = client.patch(
        "/admin/admins/flexible_admin/permissions",
        json={"permissions": ["payouts", "places"]},
        headers=_auth_headers(principal_token),
    )
    assert resp.status_code == 200
    assert sorted(resp.json()["admin_permissions"]) == ["payouts", "places"]
    assert client.get("/places/pending", headers=_auth_headers(admin_token)).status_code == 200

    # Retrieve (remove) a privilege.
    resp = client.patch(
        "/admin/admins/flexible_admin/permissions",
        json={"permissions": []},
        headers=_auth_headers(principal_token),
    )
    assert resp.status_code == 200
    assert resp.json()["admin_permissions"] == []
    assert client.get("/places/pending", headers=_auth_headers(admin_token)).status_code == 403
    assert client.get("/admin/payouts", headers=_auth_headers(admin_token)).status_code == 403


def test_principal_can_fully_revoke_admin(client):
    principal_token = _register_verify_login(client, "principal5")
    _make_principal("principal5")
    admin_token = _register_verify_login(client, "revoke_me")
    client.post(
        "/admin/admins/revoke_me/promote",
        json={"permissions": ["payouts"]},
        headers=_auth_headers(principal_token),
    )
    assert client.get("/admin/payouts", headers=_auth_headers(admin_token)).status_code == 200

    resp = client.post("/admin/admins/revoke_me/revoke", headers=_auth_headers(principal_token))
    assert resp.status_code == 200

    assert client.get("/admin/payouts", headers=_auth_headers(admin_token)).status_code == 403
    users = storage.read_all(storage.USERS_FILE)
    target = next(u for u in users if u["username"] == "revoke_me")
    assert target["is_admin"] is False


def test_principal_admin_cannot_revoke_self(client):
    principal_token = _register_verify_login(client, "principal6")
    _make_principal("principal6")

    resp = client.post("/admin/admins/principal6/revoke", headers=_auth_headers(principal_token))
    assert resp.status_code == 400


def test_promote_rejects_unknown_permission(client):
    principal_token = _register_verify_login(client, "principal7")
    _make_principal("principal7")
    _register_verify_login(client, "someone")

    resp = client.post(
        "/admin/admins/someone/promote",
        json={"permissions": ["delete_everything"]},
        headers=_auth_headers(principal_token),
    )
    assert resp.status_code == 400


def test_search_users_for_promotion(client):
    principal_token = _register_verify_login(client, "principal8")
    _make_principal("principal8")
    _register_verify_login(client, "findable_traveler")

    resp = client.get("/admin/admins/search?q=findable", headers=_auth_headers(principal_token))
    assert resp.status_code == 200
    usernames = [u["username"] for u in resp.json()]
    assert "findable_traveler" in usernames


def test_get_me_includes_admin_fields(client):
    """Regression test: UserPublic used to omit is_admin entirely, so
    /users/me never told the frontend a real admin was an admin — the
    hidden admin dashboard's `user.is_admin` check was always false."""
    token = _register_verify_login(client, "field_check_user")
    resp = client.get("/users/me", headers=_auth_headers(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_admin"] is False
    assert body["is_principal_admin"] is False
    assert body["admin_permissions"] == []

    users = storage.read_all(storage.USERS_FILE)
    for u in users:
        if u["username"] == "field_check_user":
            u["is_admin"] = True
            u["is_principal_admin"] = True
            u["admin_permissions"] = ["payouts"]
    storage.replace_all(storage.USERS_FILE, users)

    resp = client.get("/users/me", headers=_auth_headers(token))
    body = resp.json()
    assert body["is_admin"] is True
    assert body["is_principal_admin"] is True
    assert body["admin_permissions"] == ["payouts"]


def test_bootstrap_only_creates_one_principal_admin(client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "ADMIN_BOOTSTRAP_SECRET", "test-secret")
    _register_verify_login(client, "first_principal")
    _register_verify_login(client, "second_hopeful")

    resp1 = client.post(
        "/auth/admin/bootstrap", json={"username": "first_principal", "secret": "test-secret"}
    )
    assert resp1.status_code == 200

    resp2 = client.post(
        "/auth/admin/bootstrap", json={"username": "second_hopeful", "secret": "test-secret"}
    )
    assert resp2.status_code == 409

    users = storage.read_all(storage.USERS_FILE)
    principals = [u for u in users if u.get("is_principal_admin")]
    assert len(principals) == 1
    assert principals[0]["username"] == "first_principal"
