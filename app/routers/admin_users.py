"""
app/routers/admin_users.py

Principal-admin-only endpoints for managing *other* admins: promoting a
regular user to admin, revoking admin access, and granting/retrieving
specific privileges (payouts / places / feedback) for an existing admin.

Every route here is gated by get_current_principal_admin, not just
get_current_admin — a regular admin (even one with every individual
permission granted) cannot create, demote, or re-permission another
admin. That power belongs only to the principal admin, and there is
exactly one principal admin in the system at a time (see
_ensure_single_principal below and the bootstrap-endpoint change in
auth.py).
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app import storage
from app import audit
from app.dependencies import ADMIN_PERMISSIONS, get_current_principal_admin
from app.schemas import AdminPermissionsUpdate, AdminPromoteRequest, AdminUserOut, UserSearchResult

router = APIRouter(prefix="/admin/admins", tags=["admin-management"])


def _validate_permissions(permissions: list[str]) -> list[str]:
    unknown = set(permissions) - ADMIN_PERMISSIONS
    if unknown:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Unknown permission(s): {', '.join(sorted(unknown))}. "
            f"Valid permissions: {', '.join(sorted(ADMIN_PERMISSIONS))}",
        )
    # De-dupe while keeping things predictable/orderable for the UI.
    return sorted(set(permissions))


@router.get("", response_model=list[AdminUserOut])
def list_admins(principal: dict = Depends(get_current_principal_admin)):
    """Every admin account (including the principal), for the 'Manage
    admins' tab."""
    users = storage.read_all(storage.USERS_FILE)
    return [
        AdminUserOut(
            username=u["username"],
            email=u.get("email"),
            is_principal_admin=u.get("is_principal_admin", False),
            admin_permissions=u.get("admin_permissions") or [],
            promoted_at=u.get("admin_promoted_at"),
        )
        for u in users
        if u.get("is_admin")
    ]


@router.get("/search", response_model=list[UserSearchResult])
def search_users(q: str, principal: dict = Depends(get_current_principal_admin)):
    """Look up non-admin accounts by username substring, to promote one."""
    q_lower = q.strip().lower()
    if not q_lower:
        return []
    users = storage.read_all(storage.USERS_FILE)
    matches = [u for u in users if q_lower in u["username"].lower()]
    return [
        UserSearchResult(username=u["username"], email=u.get("email"), is_admin=u.get("is_admin", False))
        for u in matches[:20]
    ]


@router.post("/{username}/promote", response_model=AdminUserOut)
def promote_admin(
    username: str,
    payload: AdminPromoteRequest,
    principal: dict = Depends(get_current_principal_admin),
):
    users = storage.read_all(storage.USERS_FILE)
    target = next((u for u in users if u["username"] == username), None)
    if not target:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if target.get("is_admin"):
        raise HTTPException(status.HTTP_409_CONFLICT, "User is already an admin")

    permissions = _validate_permissions(payload.permissions)
    updates = {
        "is_admin": True,
        "is_principal_admin": False,  # only bootstrap/migration can create a principal
        "admin_permissions": permissions,
        "admin_promoted_at": datetime.now(timezone.utc).isoformat(),
        "admin_promoted_by": principal["username"],
    }
    storage.update_one(storage.USERS_FILE, "username", username, updates)
    audit.log_action(
        principal["username"], "admin.promoted", target=username,
        details=f"permissions: {', '.join(permissions) or '(none)'}",
    )
    return AdminUserOut(
        username=username,
        email=target.get("email"),
        is_principal_admin=False,
        admin_permissions=permissions,
        promoted_at=updates["admin_promoted_at"],
    )


@router.patch("/{username}/permissions", response_model=AdminUserOut)
def update_admin_permissions(
    username: str,
    payload: AdminPermissionsUpdate,
    principal: dict = Depends(get_current_principal_admin),
):
    """Grant or retrieve (remove) specific privileges for an existing
    admin — send the full desired permission list each time."""
    users = storage.read_all(storage.USERS_FILE)
    target = next((u for u in users if u["username"] == username), None)
    if not target:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if not target.get("is_admin"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "User is not an admin")
    if target.get("is_principal_admin"):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "The principal admin implicitly has every permission — nothing to set",
        )

    permissions = _validate_permissions(payload.permissions)
    storage.update_one(storage.USERS_FILE, "username", username, {"admin_permissions": permissions})
    audit.log_action(
        principal["username"], "admin.permissions_updated", target=username,
        details=f"permissions: {', '.join(permissions) or '(none)'}",
    )
    return AdminUserOut(
        username=username,
        email=target.get("email"),
        is_principal_admin=False,
        admin_permissions=permissions,
        promoted_at=target.get("admin_promoted_at"),
    )


@router.post("/{username}/revoke")
def revoke_admin(username: str, principal: dict = Depends(get_current_principal_admin)):
    if username == principal["username"]:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The principal admin cannot revoke themselves")

    users = storage.read_all(storage.USERS_FILE)
    target = next((u for u in users if u["username"] == username), None)
    if not target:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if not target.get("is_admin"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "User is not an admin")
    if target.get("is_principal_admin"):
        # Structurally can't happen given the self-revoke check above (there's
        # only ever one principal), but guard explicitly in case that ever changes.
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot revoke the principal admin")

    storage.update_one(
        storage.USERS_FILE,
        "username",
        username,
        {"is_admin": False, "admin_permissions": [], "admin_promoted_at": None, "admin_promoted_by": None},
    )
    audit.log_action(principal["username"], "admin.revoked", target=username)
    return {"detail": f"Admin access revoked for {username}"}
