"""
app/routers/admin_overview.py

The "everything an admin needs to see" surface:
  GET    /admin/users                 -> full directory (filter by
                                          verified / locked / admin / search)
  POST   /admin/users/{username}/lock
  POST   /admin/users/{username}/unlock
  DELETE /admin/users/{username}
  GET    /admin/logs                  -> audit trail
  GET    /admin/overview              -> system-wide stats + background
                                          job status, for the dashboard's
                                          landing tab

Permission model:
  - list/lock/unlock/delete require the "users" permission
  - audit log requires the "logs" permission
  - the overview stats are visible to ANY admin regardless of specific
    permissions (it's just a read-only summary, not a sensitive action)
  - locking, unlocking, or deleting an *admin* account is principal-only,
    even for a "users"-permission admin — same reasoning as admin_users.py:
    that power shouldn't be delegable to just anyone with the users
    permission, since it could be used to disable a fellow admin
  - the principal admin can never be locked or deleted through this
    router, by anyone, including themselves
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app import audit, storage
from app.cleanup import get_cleanup_status
from app.dependencies import get_current_admin, get_current_principal_admin, require_permission
from app.schemas import AdminLockRequest, AdminUserDetail, AuditLogEntry, SystemOverview

router = APIRouter(prefix="/admin", tags=["admin-overview"])


def _to_detail(u: dict) -> AdminUserDetail:
    return AdminUserDetail(
        username=u["username"],
        email=u.get("email"),
        phone=u.get("phone"),
        is_verified=u.get("is_verified", False),
        is_locked=u.get("is_locked", False),
        is_admin=u.get("is_admin", False),
        is_principal_admin=u.get("is_principal_admin", False),
        admin_permissions=u.get("admin_permissions") or [],
        mfa_enabled=u.get("mfa_enabled", False),
        created_at=u["created_at"],
        referral_code=u["referral_code"],
    )


@router.get("/users", response_model=list[AdminUserDetail])
def list_users(
    verified: bool | None = Query(default=None),
    locked: bool | None = Query(default=None),
    admin_only: bool | None = Query(default=None, alias="admin"),
    q: str | None = Query(default=None, description="Substring match on username or email"),
    admin: dict = Depends(require_permission("users")),
):
    users = storage.read_all(storage.USERS_FILE)

    if verified is not None:
        users = [u for u in users if u.get("is_verified", False) == verified]
    if locked is not None:
        users = [u for u in users if u.get("is_locked", False) == locked]
    if admin_only is not None:
        users = [u for u in users if u.get("is_admin", False) == admin_only]
    if q:
        q_lower = q.strip().lower()
        users = [
            u for u in users
            if q_lower in u["username"].lower() or q_lower in (u.get("email") or "").lower()
        ]

    users.sort(key=lambda u: u["created_at"], reverse=True)
    return [_to_detail(u) for u in users]


def _get_target_or_404(username: str) -> dict:
    users = storage.read_all(storage.USERS_FILE)
    target = next((u for u in users if u["username"] == username), None)
    if not target:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return target


@router.post("/users/{username}/lock", response_model=AdminUserDetail)
def lock_user(username: str, payload: AdminLockRequest, admin: dict = Depends(require_permission("users"))):
    if username == admin["username"]:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot lock your own account")

    target = _get_target_or_404(username)
    if target.get("is_principal_admin"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot lock the principal admin")
    if target.get("is_admin") and not admin.get("is_principal_admin"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the principal admin can lock another admin's account")

    storage.update_one(storage.USERS_FILE, "username", username, {"is_locked": True})
    audit.log_action(admin["username"], "user.locked", target=username, details=payload.reason)
    return _to_detail({**target, "is_locked": True})


@router.post("/users/{username}/unlock", response_model=AdminUserDetail)
def unlock_user(username: str, admin: dict = Depends(require_permission("users"))):
    target = _get_target_or_404(username)
    if target.get("is_admin") and not admin.get("is_principal_admin"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the principal admin can unlock another admin's account")

    storage.update_one(storage.USERS_FILE, "username", username, {"is_locked": False})
    audit.log_action(admin["username"], "user.unlocked", target=username)
    return _to_detail({**target, "is_locked": False})


@router.delete("/users/{username}", status_code=status.HTTP_200_OK)
def delete_user(username: str, admin: dict = Depends(require_permission("users"))):
    if username == admin["username"]:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Use your own account settings to delete yourself")

    target = _get_target_or_404(username)
    if target.get("is_principal_admin"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot delete the principal admin")
    if target.get("is_admin") and not admin.get("is_principal_admin"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the principal admin can delete another admin's account")

    storage.delete_one(storage.USERS_FILE, "username", username)
    # Scrub owned records so no orphaned personal data lingers (same as
    # the user's own DELETE /users/me does for itself).
    itineraries = storage.read_all(storage.ITINERARIES_FILE)
    storage.replace_all(
        storage.ITINERARIES_FILE, [it for it in itineraries if it.get("username") != username]
    )
    audit.log_action(admin["username"], "user.deleted", target=username)
    return {"detail": f"Account '{username}' deleted"}


@router.get("/logs", response_model=list[AuditLogEntry])
def list_audit_logs(
    action: str | None = Query(default=None, description="Filter by exact action name, e.g. 'user.locked'"),
    actor: str | None = Query(default=None),
    target: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    admin: dict = Depends(require_permission("logs")),
):
    entries = storage.read_all(storage.AUDIT_LOG_FILE)
    if action:
        entries = [e for e in entries if e["action"] == action]
    if actor:
        entries = [e for e in entries if e["actor"] == actor]
    if target:
        entries = [e for e in entries if e.get("target") == target]
    entries.sort(key=lambda e: e["created_at"], reverse=True)
    return [AuditLogEntry(**e) for e in entries[:limit]]


@router.get("/overview", response_model=SystemOverview)
def system_overview(admin: dict = Depends(get_current_admin)):
    """Read-only dashboard summary — visible to any admin regardless of
    which specific permissions they hold."""
    from datetime import datetime, timedelta, timezone

    users = storage.read_all(storage.USERS_FILE)
    payouts = storage.read_all(storage.PAYOUTS_FILE)
    places = storage.read_all(storage.PLACES_FILE)
    feedback = storage.read_all(storage.FEEDBACK_FILE)
    notifications = storage.read_all(storage.NOTIFICATIONS_FILE)

    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    def _within_7d(iso_ts: str) -> bool:
        try:
            return datetime.fromisoformat(iso_ts) >= week_ago
        except (ValueError, TypeError):
            return False

    ratings = [f.get("rating") for f in feedback if f.get("rating") is not None]

    return SystemOverview(
        total_users=len(users),
        verified_users=sum(1 for u in users if u.get("is_verified")),
        unverified_users=sum(1 for u in users if not u.get("is_verified")),
        locked_users=sum(1 for u in users if u.get("is_locked")),
        total_admins=sum(1 for u in users if u.get("is_admin")),
        pending_payouts=sum(1 for p in payouts if p["status"] == "pending"),
        approved_payouts_total_usd=round(sum(p["amount_usd"] for p in payouts if p["status"] == "approved"), 2),
        pending_place_submissions=sum(1 for p in places if p["status"] == "pending"),
        total_feedback=len(feedback),
        average_feedback_rating=round(sum(ratings) / len(ratings), 2) if ratings else None,
        notifications_sent_last_7d=sum(1 for n in notifications if _within_7d(n["created_at"])),
        new_registrations_last_7d=sum(1 for u in users if _within_7d(u["created_at"])),
        background_jobs=[get_cleanup_status()],
    )
