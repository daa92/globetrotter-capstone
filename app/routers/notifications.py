"""
app/routers/notifications.py

The in-app notification center: "a notification button/section... where
he can see any notifications, mark them as read or delete them (1, some,
or all)."

  GET    /notifications                 -> list yours (newest first)
  GET    /notifications/unread-count    -> just the count, for a bell badge
  POST   /notifications/mark-read       -> {ids:[...]} or {all:true}
  DELETE /notifications/{id}            -> delete exactly one
  POST   /notifications/delete          -> {ids:[...]} or {all:true} (bulk)

  POST   /admin/notifications/send      -> admin pushes to specific users
                                            (unicast: one username, multicast:
                                            several) or everyone (broadcast)
  GET    /admin/notifications/sent      -> history of admin-sent batches
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app import audit, storage
from app.dependencies import get_current_user, require_permission
from app.notifications import outbox
from app.notifications.service import create_for_many
from app.schemas import AdminSendNotificationRequest, NotificationBatchAction, NotificationBatchOut, NotificationOut

router = APIRouter(tags=["notifications"])


@router.get("/notifications", response_model=list[NotificationOut])
def list_notifications(unread_only: bool = Query(default=False), user: dict = Depends(get_current_user)):
    notifications = [n for n in storage.read_all(storage.NOTIFICATIONS_FILE) if n["username"] == user["username"]]
    if unread_only:
        notifications = [n for n in notifications if not n["is_read"]]
    notifications.sort(key=lambda n: n["created_at"], reverse=True)
    return [NotificationOut(**n) for n in notifications]


@router.get("/notifications/unread-count")
def unread_count(user: dict = Depends(get_current_user)):
    notifications = [n for n in storage.read_all(storage.NOTIFICATIONS_FILE) if n["username"] == user["username"]]
    return {"unread_count": sum(1 for n in notifications if not n["is_read"])}


def _resolve_own_ids(payload: NotificationBatchAction, username: str) -> set:
    """Returns the set of notification IDs to act on, scoped to the caller's
    own notifications only — never trust a client-supplied ID list blindly,
    someone could pass another user's notification ID."""
    own_ids = {
        n["id"] for n in storage.read_all(storage.NOTIFICATIONS_FILE) if n["username"] == username
    }
    if payload.all:
        return own_ids
    if not payload.ids:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Provide 'ids' or set 'all': true")
    requested = set(payload.ids)
    return requested & own_ids  # silently drop any ID that isn't actually theirs


@router.post("/notifications/mark-read")
def mark_read(payload: NotificationBatchAction, user: dict = Depends(get_current_user)):
    ids = _resolve_own_ids(payload, user["username"])
    updated = storage.update_many(storage.NOTIFICATIONS_FILE, "id", ids, {"is_read": True})
    return {"marked_read": updated}


@router.delete("/notifications/{notification_id}")
def delete_one_notification(notification_id: str, user: dict = Depends(get_current_user)):
    notifications = storage.read_all(storage.NOTIFICATIONS_FILE)
    match = next((n for n in notifications if n["id"] == notification_id), None)
    if not match:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Notification not found")
    if match["username"] != user["username"]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your notification")
    storage.delete_one(storage.NOTIFICATIONS_FILE, "id", notification_id)
    return None


@router.post("/notifications/delete")
def delete_many_notifications(payload: NotificationBatchAction, user: dict = Depends(get_current_user)):
    ids = _resolve_own_ids(payload, user["username"])
    deleted = storage.delete_many(storage.NOTIFICATIONS_FILE, "id", ids)
    return {"deleted": deleted}


# ---------------------------------------------------------------------------
# Admin: push notifications to users
# ---------------------------------------------------------------------------

@router.post("/admin/notifications/send", status_code=status.HTTP_201_CREATED)
def admin_send_notification(payload: AdminSendNotificationRequest, admin: dict = Depends(require_permission("notifications"))):
    users = storage.read_all(storage.USERS_FILE)

    if payload.broadcast:
        targets = users
    else:
        if not payload.usernames:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Provide 'usernames' or set 'broadcast': true")
        targets = [u for u in users if u["username"] in payload.usernames]
        missing = set(payload.usernames) - {u["username"] for u in targets}
        if missing:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown username(s): {', '.join(missing)}")

    usernames = [u["username"] for u in targets]
    created = create_for_many(usernames, payload.title, payload.message, category="admin", sent_by=admin["username"])

    emailed = 0
    if payload.also_email:
        for u in targets:
            if u.get("email"):
                outbox.send(to=u["email"], subject=payload.title, body=payload.message)
                emailed += 1

    audience = "broadcast" if payload.broadcast else ("unicast" if len(usernames) == 1 else "multicast")
    batch = {
        "id": str(uuid.uuid4()),
        "title": payload.title,
        "message": payload.message,
        "audience": audience,
        "recipient_count": len(usernames),
        "sent_by": admin["username"],
        "also_email": payload.also_email,
        "emailed_count": emailed,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    storage.append(storage.NOTIFICATION_BATCHES_FILE, batch)
    audit.log_action(
        admin["username"], "notification.sent", target=audience,
        details=f"'{payload.title}' to {len(usernames)} recipient(s)",
    )

    return {"notified": len(created), "emailed": emailed}


@router.get("/admin/notifications/sent", response_model=list[NotificationBatchOut])
def list_sent_notifications(
    limit: int = Query(default=100, ge=1, le=500),
    admin: dict = Depends(require_permission("notifications")),
):
    """History of admin-sent notification batches (unicast/multicast/
    broadcast), newest first — so sending isn't a one-way, unauditable action."""
    batches = storage.read_all(storage.NOTIFICATION_BATCHES_FILE)
    batches.sort(key=lambda b: b["created_at"], reverse=True)
    return [NotificationBatchOut(**b) for b in batches[:limit]]
