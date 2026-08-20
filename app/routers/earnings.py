"""
app/routers/earnings.py

Implements: "if a user uses the app at least 5 min/day, they earn $0.50/day"
plus the referral bonus ($0.25/verified referral) and the payout system
(min $30, requiring 5 referrals + 5 good-rated feedback submissions).

Design notes:
  - Activity is tracked via a lightweight heartbeat the frontend/CLI calls
    periodically while the user is actively using the app (see
    MAX_HEARTBEAT_INCREMENT_SECONDS in config — caps how much a single
    call can add, so a client can't just claim "10000 seconds elapsed").
  - Earnings are always *computed* from the underlying activity/referral/
    payout records, never stored as a running balance — this avoids an
    entire class of bugs where the balance and the records it's supposed
    to represent drift out of sync, which matters a lot given Phase 1's
    JSON storage has no transactions to keep two writes consistent.
  - "Good feedback" = a feedback submission with rating >= GOOD_FEEDBACK_MIN_RATING.
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app import storage
from app import audit
from app.config import settings
from app.dependencies import get_current_user, require_permission
from app.notifications.service import create_notification
from app.schemas import (
    DailyActivity,
    EarningsResponse,
    HeartbeatRequest,
    PayoutEligibility,
    PayoutRequestResult,
    RequirementStatus,
)

router = APIRouter(tags=["earnings"])


def _today_str() -> str:
    return datetime.now(timezone.utc).date().isoformat()


@router.post("/users/me/activity/heartbeat")
def heartbeat(payload: HeartbeatRequest, user: dict = Depends(get_current_user)):
    elapsed = min(payload.elapsed_seconds, settings.MAX_HEARTBEAT_INCREMENT_SECONDS)
    today = _today_str()

    records = storage.read_all(storage.ACTIVITY_FILE)
    existing = next((r for r in records if r["username"] == user["username"] and r["date"] == today), None)

    if existing:
        existing["active_seconds"] += elapsed
        storage.replace_all(storage.ACTIVITY_FILE, records)
        active_seconds = existing["active_seconds"]
    else:
        active_seconds = elapsed
        storage.append(storage.ACTIVITY_FILE, {
            "username": user["username"], "date": today, "active_seconds": active_seconds,
        })

    return {
        "date": today,
        "active_seconds": active_seconds,
        "threshold_seconds": settings.DAILY_USAGE_THRESHOLD_SECONDS,
        "threshold_met": active_seconds >= settings.DAILY_USAGE_THRESHOLD_SECONDS,
    }


def _compute_earnings(username: str) -> dict:
    activity = [r for r in storage.read_all(storage.ACTIVITY_FILE) if r["username"] == username]
    activity.sort(key=lambda r: r["date"])

    daily_log = [
        DailyActivity(
            date=r["date"],
            active_seconds=r["active_seconds"],
            qualified=r["active_seconds"] >= settings.DAILY_USAGE_THRESHOLD_SECONDS,
        )
        for r in activity
    ]
    qualifying_days = sum(1 for d in daily_log if d.qualified)
    usage_earnings = round(qualifying_days * settings.DAILY_USAGE_BONUS_USD, 2)

    referrals = [r for r in storage.read_all(storage.REFERRALS_FILE) if r["sponsor_username"] == username]
    referral_count = len(referrals)
    referral_earnings = round(sum(r["amount_usd"] for r in referrals), 2)

    feedback = [f for f in storage.read_all(storage.FEEDBACK_FILE) if f["username"] == username]
    good_feedback_count = sum(1 for f in feedback if (f.get("rating") or 0) >= settings.GOOD_FEEDBACK_MIN_RATING)

    total_earned = round(usage_earnings + referral_earnings, 2)

    payouts = [p for p in storage.read_all(storage.PAYOUTS_FILE) if p["username"] == username]
    total_paid_out = round(sum(p["amount_usd"] for p in payouts if p["status"] == "approved"), 2)
    has_pending_payout = any(p["status"] == "pending" for p in payouts)

    available_usd = round(total_earned - total_paid_out, 2)
    available_fcfa = round(available_usd * settings.FCFA_PER_USD, 2)

    today = _today_str()
    today_record = next((r for r in activity if r["date"] == today), None)
    today_active_seconds = today_record["active_seconds"] if today_record else 0

    eligibility = PayoutEligibility(
        eligible=(
            available_usd >= settings.MIN_PAYOUT_USD
            and referral_count >= settings.MIN_REFERRALS_FOR_PAYOUT
            and good_feedback_count >= settings.MIN_GOOD_FEEDBACK_FOR_PAYOUT
            and not has_pending_payout
        ),
        balance=RequirementStatus(met=available_usd >= settings.MIN_PAYOUT_USD, have=available_usd, need=settings.MIN_PAYOUT_USD),
        referrals=RequirementStatus(met=referral_count >= settings.MIN_REFERRALS_FOR_PAYOUT, have=referral_count, need=settings.MIN_REFERRALS_FOR_PAYOUT),
        good_feedback=RequirementStatus(met=good_feedback_count >= settings.MIN_GOOD_FEEDBACK_FOR_PAYOUT, have=good_feedback_count, need=settings.MIN_GOOD_FEEDBACK_FOR_PAYOUT),
        has_pending_payout=has_pending_payout,
    )

    return {
        "qualifying_days": qualifying_days,
        "usage_earnings_usd": usage_earnings,
        "referral_count": referral_count,
        "referral_earnings_usd": referral_earnings,
        "good_feedback_count": good_feedback_count,
        "total_earned_usd": total_earned,
        "total_paid_out_usd": total_paid_out,
        "available_usd": available_usd,
        "available_fcfa": available_fcfa,
        "fcfa_rate": settings.FCFA_PER_USD,
        "today_active_seconds": today_active_seconds,
        "today_threshold_seconds": settings.DAILY_USAGE_THRESHOLD_SECONDS,
        "daily_log": daily_log,
        "payout_eligibility": eligibility,
    }


@router.get("/users/me/earnings", response_model=EarningsResponse)
def get_earnings(user: dict = Depends(get_current_user)):
    data = _compute_earnings(user["username"])
    return EarningsResponse(
        referral_code=user["referral_code"],
        referral_link=f"{settings.FRONTEND_URL}/register?ref={user['referral_code']}",
        **data,
    )


@router.post("/users/me/payouts/request", response_model=PayoutRequestResult, status_code=status.HTTP_201_CREATED)
def request_payout(user: dict = Depends(get_current_user)):
    data = _compute_earnings(user["username"])
    eligibility: PayoutEligibility = data["payout_eligibility"]

    if not eligibility.eligible:
        unmet = []
        if not eligibility.balance.met:
            unmet.append(f"balance ${eligibility.balance.have} < ${eligibility.balance.need}")
        if not eligibility.referrals.met:
            unmet.append(f"referrals {eligibility.referrals.have} < {eligibility.referrals.need}")
        if not eligibility.good_feedback.met:
            unmet.append(f"good feedback {eligibility.good_feedback.have} < {eligibility.good_feedback.need}")
        if eligibility.has_pending_payout:
            unmet.append("a payout request is already pending")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Not eligible for payout: {'; '.join(unmet)}")

    payout = {
        "id": str(uuid.uuid4()),
        "username": user["username"],
        "amount_usd": data["available_usd"],
        "status": "pending",
        "requested_at": datetime.now(timezone.utc).isoformat(),
    }
    storage.append(storage.PAYOUTS_FILE, payout)
    return PayoutRequestResult(
        id=payout["id"],
        amount_usd=payout["amount_usd"],
        amount_fcfa=round(payout["amount_usd"] * settings.FCFA_PER_USD, 2),
        status=payout["status"],
        requested_at=payout["requested_at"],
    )


# ---------------------------------------------------------------------------
# Admin: review payout requests
# ---------------------------------------------------------------------------

@router.get("/admin/payouts")
def list_payouts(status_filter: str = "pending", admin: dict = Depends(require_permission("payouts"))):
    payouts = storage.read_all(storage.PAYOUTS_FILE)
    if status_filter == "all":
        return payouts
    return [p for p in payouts if p["status"] == status_filter]


@router.post("/admin/payouts/{payout_id}/approve")
def approve_payout(payout_id: str, admin: dict = Depends(require_permission("payouts"))):
    payouts = storage.read_all(storage.PAYOUTS_FILE)
    payout = next((p for p in payouts if p["id"] == payout_id), None)
    if not payout:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Payout request not found")
    storage.update_one(storage.PAYOUTS_FILE, "id", payout_id, {"status": "approved"})
    audit.log_action(admin["username"], "payout.approved", target=payout["username"], details=f"${payout['amount_usd']}")
    create_notification(
        username=payout["username"],
        title="Payout approved",
        message=f"Your payout request for ${payout['amount_usd']} has been approved.",
        category="payout",
    )
    return {"detail": "Payout approved"}


@router.post("/admin/payouts/{payout_id}/reject")
def reject_payout(payout_id: str, admin: dict = Depends(require_permission("payouts"))):
    payouts = storage.read_all(storage.PAYOUTS_FILE)
    payout = next((p for p in payouts if p["id"] == payout_id), None)
    if not payout:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Payout request not found")
    storage.update_one(storage.PAYOUTS_FILE, "id", payout_id, {"status": "rejected"})
    audit.log_action(admin["username"], "payout.rejected", target=payout["username"], details=f"${payout['amount_usd']}")
    create_notification(
        username=payout["username"],
        title="Payout request rejected",
        message=f"Your payout request for ${payout['amount_usd']} was rejected. Contact support for details.",
        category="payout",
    )
    return {"detail": "Payout rejected"}
