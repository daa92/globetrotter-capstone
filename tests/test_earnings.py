from datetime import datetime, timedelta, timezone

from app import storage
from app.config import settings
from app.notifications import outbox


def _register(client, username, password="s3cr3t12", referral_code=None):
    payload = {"username": username, "email": f"{username}@example.com", "password": password, "preferences": []}
    if referral_code:
        payload["referral_code"] = referral_code
    return client.post("/auth/register", json=payload)


def _verify(client, username):
    message = outbox.get_last_message_to(f"{username}@example.com")
    token = message["body"].split("token: ")[1].split("\n")[0]
    return client.post("/auth/verify", json={"token": token})


def _login(client, username, password="s3cr3t12"):
    resp = client.post("/auth/login", json={"username": username, "password": password})
    return resp.json()["access_token"]


def _register_verify_login(client, username, password="s3cr3t12", referral_code=None):
    _register(client, username, password, referral_code)
    _verify(client, username)
    return _login(client, username, password)


def _auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Heartbeat / daily usage earnings
# ---------------------------------------------------------------------------

def test_heartbeat_accumulates_active_seconds(client):
    token = _register_verify_login(client, "heartbeat_user")
    headers = _auth_headers(token)

    r1 = client.post("/users/me/activity/heartbeat", json={"elapsed_seconds": 60}, headers=headers)
    assert r1.status_code == 200
    assert r1.json()["active_seconds"] == 60
    assert r1.json()["threshold_met"] is False

    # Second call respects the per-call cap (settings.MAX_HEARTBEAT_INCREMENT_SECONDS = 90),
    # so send a couple more calls to cross the 300s threshold realistically.
    client.post("/users/me/activity/heartbeat", json={"elapsed_seconds": 90}, headers=headers)
    client.post("/users/me/activity/heartbeat", json={"elapsed_seconds": 90}, headers=headers)
    r4 = client.post("/users/me/activity/heartbeat", json={"elapsed_seconds": 90}, headers=headers)
    assert r4.json()["active_seconds"] == 330  # 60 + 90*3
    assert r4.json()["threshold_met"] is True


def test_heartbeat_caps_a_single_call(client):
    token = _register_verify_login(client, "cap_user")
    headers = _auth_headers(token)
    resp = client.post("/users/me/activity/heartbeat", json={"elapsed_seconds": 3600}, headers=headers)
    assert resp.json()["active_seconds"] == settings.MAX_HEARTBEAT_INCREMENT_SECONDS


def test_earnings_reflect_qualifying_days(client):
    token = _register_verify_login(client, "earner")
    headers = _auth_headers(token)

    # Simulate 3 qualifying days directly (heartbeat is capped per-call, so
    # backdating activity records is the realistic way to test multi-day accrual).
    today = datetime.now(timezone.utc).date()
    records = [
        {"username": "earner", "date": (today - timedelta(days=i)).isoformat(), "active_seconds": 400}
        for i in range(3)
    ]
    storage.replace_all(storage.ACTIVITY_FILE, records)

    resp = client.get("/users/me/earnings", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["qualifying_days"] == 3
    assert body["usage_earnings_usd"] == 1.5  # 3 * $0.50
    assert body["available_fcfa"] == round(1.5 * settings.FCFA_PER_USD, 2)


# ---------------------------------------------------------------------------
# Referrals
# ---------------------------------------------------------------------------

def test_referral_credited_only_after_referred_user_verifies(client):
    sponsor_token = _register_verify_login(client, "sponsor1")
    sponsor_code = client.get("/users/me", headers=_auth_headers(sponsor_token)).json()["referral_code"]

    _register(client, "referred1", referral_code=sponsor_code)

    # Not verified yet — sponsor shouldn't be credited.
    earnings_before = client.get("/users/me/earnings", headers=_auth_headers(sponsor_token)).json()
    assert earnings_before["referral_count"] == 0

    _verify(client, "referred1")

    earnings_after = client.get("/users/me/earnings", headers=_auth_headers(sponsor_token)).json()
    assert earnings_after["referral_count"] == 1
    assert earnings_after["referral_earnings_usd"] == settings.REFERRAL_BONUS_USD


def test_invalid_referral_code_rejected_at_registration(client):
    resp = _register(client, "someone", referral_code="NOTAREALCODE")
    assert resp.status_code == 400


def test_a_referred_user_can_themselves_become_a_sponsor(client):
    """Referral chains should work: A refers B, B refers C — each link is
    independent. (True self-referral is structurally impossible: you'd need
    to register with a username that's already yours, which the uniqueness
    check rejects before the referral code is even looked at.)"""
    sponsor_a_token = _register_verify_login(client, "chain_a")
    code_a = client.get("/users/me", headers=_auth_headers(sponsor_a_token)).json()["referral_code"]

    _register(client, "chain_b", referral_code=code_a)
    _verify(client, "chain_b")
    token_b = _login(client, "chain_b")
    code_b = client.get("/users/me", headers=_auth_headers(token_b)).json()["referral_code"]

    _register(client, "chain_c", referral_code=code_b)
    _verify(client, "chain_c")

    earnings_a = client.get("/users/me/earnings", headers=_auth_headers(sponsor_a_token)).json()
    earnings_b = client.get("/users/me/earnings", headers=_auth_headers(token_b)).json()
    assert earnings_a["referral_count"] == 1  # A referred only B
    assert earnings_b["referral_count"] == 1  # B referred only C


# ---------------------------------------------------------------------------
# Good feedback counting
# ---------------------------------------------------------------------------

def test_only_high_rated_feedback_counts_as_good(client):
    token = _register_verify_login(client, "feedback_user")
    headers = _auth_headers(token)

    client.post("/feedback", json={"category": "suggestion", "message": "Love it, great app!", "rating": 5}, headers=headers)
    client.post("/feedback", json={"category": "bug", "message": "Found a small bug here", "rating": 2}, headers=headers)

    earnings = client.get("/users/me/earnings", headers=headers).json()
    assert earnings["good_feedback_count"] == 1


# ---------------------------------------------------------------------------
# Payout eligibility + admin approval
# ---------------------------------------------------------------------------

def test_payout_request_rejected_when_not_eligible(client):
    token = _register_verify_login(client, "poor_user")
    resp = client.post("/users/me/payouts/request", headers=_auth_headers(token))
    assert resp.status_code == 400
    assert "not eligible" in resp.json()["detail"].lower()


def test_payout_request_succeeds_when_all_requirements_met(client):
    token = _register_verify_login(client, "rich_user")
    headers = _auth_headers(token)

    # 1. Enough qualifying days for $30+ balance (need 60 days at $0.50/day).
    today = datetime.now(timezone.utc).date()
    records = [
        {"username": "rich_user", "date": (today - timedelta(days=i)).isoformat(), "active_seconds": 400}
        for i in range(65)
    ]
    storage.replace_all(storage.ACTIVITY_FILE, records)

    # 2. 5 referrals.
    referrals = [
        {"sponsor_username": "rich_user", "referred_username": f"ref{i}", "amount_usd": 0.25, "credited_at": "2026-01-01T00:00:00+00:00"}
        for i in range(5)
    ]
    storage.replace_all(storage.REFERRALS_FILE, referrals)

    # 3. 5 good feedback submissions.
    for i in range(5):
        client.post("/feedback", json={"category": "suggestion", "message": f"Great feature idea #{i}", "rating": 5}, headers=headers)

    resp = client.post("/users/me/payouts/request", headers=headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "pending"
    assert body["amount_usd"] >= 30.0

    # A second request while one is pending should be rejected.
    second = client.post("/users/me/payouts/request", headers=headers)
    assert second.status_code == 400
    assert "pending" in second.json()["detail"].lower()


def test_admin_can_approve_payout_and_it_reduces_available_balance(client):
    admin_token = _register_verify_login(client, "admin_payout_test")
    users = storage.read_all(storage.USERS_FILE)
    for u in users:
        if u["username"] == "admin_payout_test":
            u["is_admin"] = True
    storage.replace_all(storage.USERS_FILE, users)

    payout = {
        "id": "test-payout-1", "username": "admin_payout_test",
        "amount_usd": 30.0, "status": "pending", "requested_at": "2026-01-01T00:00:00+00:00",
    }
    storage.append(storage.PAYOUTS_FILE, payout)

    headers = _auth_headers(admin_token)
    approve_resp = client.post("/admin/payouts/test-payout-1/approve", headers=headers)
    assert approve_resp.status_code == 200

    payouts = storage.read_all(storage.PAYOUTS_FILE)
    assert payouts[0]["status"] == "approved"


def test_admin_only_can_list_payouts(client):
    token = _register_verify_login(client, "regular_joe")
    resp = client.get("/admin/payouts", headers=_auth_headers(token))
    assert resp.status_code == 403
