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
