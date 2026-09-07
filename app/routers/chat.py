"""
app/routers/chat.py

Real-time-ish messaging: direct chats + groups, text and multimedia
messages, full CRUD on both conversations and messages, read receipts,
and a WebSocket channel so connected clients get pushed updates instead
of having to poll (same "store" persistence pattern as every other
router — see app/storage.py — plus app/chat_ws.py for the socket side).

  GET    /chat/users/search                          -> find people to start a chat with
  GET    /chat/conversations                          -> list yours (direct + group), newest activity first
  POST   /chat/conversations                          -> start a direct chat or create a group
  GET    /chat/conversations/{id}                     -> one conversation + members
  PATCH  /chat/conversations/{id}                      -> rename a group / change its picture (JSON url)
  DELETE /chat/conversations/{id}                      -> delete a direct chat, or a group (admin only)
  POST   /chat/conversations/{id}/picture              -> upload a group picture (admin only)
  POST   /chat/conversations/{id}/members               -> add member(s) to a group (admin only)
  DELETE /chat/conversations/{id}/members/{username}    -> leave, or remove someone (admin only)
  PATCH  /chat/conversations/{id}/members/{username}    -> promote/demote a group admin
  GET    /chat/conversations/{id}/messages              -> paginated message history
  POST   /chat/conversations/{id}/messages              -> send a text message
  POST   /chat/conversations/{id}/messages/media        -> send an image/video/audio/file message
  PATCH  /chat/messages/{id}                            -> edit your own text message
  DELETE /chat/messages/{id}                            -> delete your own message (for everyone)
  POST   /chat/conversations/{id}/read                  -> mark a conversation read (read receipts)
  WS     /chat/ws?token=...                              -> live push: new/edited/deleted messages,
                                                             conversation updates, typing, read receipts
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, WebSocket, WebSocketDisconnect, status
from jose import JWTError

from app import media, security, storage
from app.chat_ws import manager
from app.dependencies import get_current_user
from app.schemas import (
    ChatConversationCreate,
    ChatConversationOut,
    ChatConversationUpdate,
    ChatMemberRoleUpdate,
    ChatMembersAdd,
    ChatMessageCreate,
    ChatMessageEdit,
    ChatMessageOut,
    ChatUserOut,
)

router = APIRouter(prefix="/chat", tags=["chat"])

MAX_AVATAR_BYTES = 5_000_000  # group picture — same cap as a user's own avatar
MAX_CHAT_MEDIA_BYTES = 20_000_000  # 20MB per attachment


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_conversation(conversation_id: str) -> dict | None:
    return next((c for c in storage.read_all(storage.CHAT_CONVERSATIONS_FILE) if c["id"] == conversation_id), None)


def _get_conversation_or_404(conversation_id: str) -> dict:
    conv = _get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    return conv


def _get_message_or_404(message_id: str) -> dict:
    msg = next((m for m in storage.read_all(storage.CHAT_MESSAGES_FILE) if m["id"] == message_id), None)
    if not msg:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Message not found")
    return msg


def _member_usernames(conv: dict) -> list[str]:
    return [m["username"] for m in conv["members"]]


def _require_member(conv: dict, username: str) -> None:
    if username not in _member_usernames(conv):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You're not part of this conversation")


def _require_admin(conv: dict, username: str) -> None:
    member = next((m for m in conv["members"] if m["username"] == username), None)
    if not member or member["role"] != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only a group admin can do this")


def _messages_for(conversation_id: str) -> list[dict]:
    return [m for m in storage.read_all(storage.CHAT_MESSAGES_FILE) if m["conversation_id"] == conversation_id]


def _users_by_username() -> dict:
    return {u["username"]: u for u in storage.read_all(storage.USERS_FILE)}


def _serialize_message(msg: dict, conv: dict) -> ChatMessageOut:
    # A member has "read" a message once their last_read_at is at or past
    # the message's timestamp — avoids storing a growing read_by array on
    # every single message.
    read_by = [
        m["username"]
        for m in conv["members"]
        if m["username"] != msg["sender"] and (m.get("last_read_at") or "") >= msg["created_at"]
    ]
    deleted = bool(msg.get("deleted"))
    return ChatMessageOut(
        id=msg["id"],
        conversation_id=msg["conversation_id"],
        sender=msg["sender"],
        type=msg["type"],
        text=None if deleted else msg.get("text"),
        media_url=None if deleted else msg.get("media_url"),
        media_type=msg.get("media_type"),
        file_name=msg.get("file_name"),
        created_at=msg["created_at"],
        edited_at=msg.get("edited_at"),
        deleted=deleted,
        read_by=read_by,
    )


def _serialize_conversation(conv: dict, requester: str, users_index: dict, msgs: list[dict]) -> ChatConversationOut:
    from app.schemas import ChatMemberOut

    members = [
        ChatMemberOut(
            username=m["username"],
            role=m["role"],
            profile_picture_url=(users_index.get(m["username"]) or {}).get("profile_picture_url"),
            joined_at=m["joined_at"],
        )
        for m in conv["members"]
    ]
    ordered = sorted(msgs, key=lambda m: m["created_at"])
    last = ordered[-1] if ordered else None
    last_out = _serialize_message(last, conv) if last else None

    my_member = next((m for m in conv["members"] if m["username"] == requester), None)
    last_read = (my_member or {}).get("last_read_at") or ""
    unread = sum(1 for m in ordered if m["sender"] != requester and m["created_at"] > last_read and not m.get("deleted"))

    return ChatConversationOut(
        id=conv["id"],
        type=conv["type"],
        name=conv.get("name"),
        picture_url=conv.get("picture_url"),
        created_by=conv["created_by"],
        created_at=conv["created_at"],
        updated_at=conv["updated_at"],
        members=members,
        last_message=last_out,
        unread_count=unread,
    )


def _touch_and_mark_read(conv: dict, username: str, now: str) -> None:
    """After sending a message, the sender has implicitly read up to now."""
    updated_members = [{**m, "last_read_at": now} if m["username"] == username else m for m in conv["members"]]
    storage.update_one(storage.CHAT_CONVERSATIONS_FILE, "id", conv["id"], {"members": updated_members, "updated_at": now})
    conv["members"] = updated_members
    conv["updated_at"] = now


# ---------------------------------------------------------------------------
# Finding people to chat with
# ---------------------------------------------------------------------------

@router.get("/users/search", response_model=list[ChatUserOut])
def search_users(
    q: str = Query(min_length=1, max_length=64),
    limit: int = Query(default=15, ge=1, le=50),
    user: dict = Depends(get_current_user),
):
    q_lower = q.lower()
    matches = [u for u in storage.read_all(storage.USERS_FILE) if u["username"] != user["username"] and q_lower in u["username"].lower()]
    matches.sort(key=lambda u: u["username"].lower())
    return [ChatUserOut(username=u["username"], profile_picture_url=u.get("profile_picture_url")) for u in matches[:limit]]


# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------

@router.get("/conversations", response_model=list[ChatConversationOut])
def list_conversations(user: dict = Depends(get_current_user)):
    username = user["username"]
    mine = [c for c in storage.read_all(storage.CHAT_CONVERSATIONS_FILE) if username in _member_usernames(c)]
    all_messages = storage.read_all(storage.CHAT_MESSAGES_FILE)
    by_conv: dict[str, list[dict]] = {}
    for m in all_messages:
        by_conv.setdefault(m["conversation_id"], []).append(m)
    users_index = _users_by_username()

    out = [_serialize_conversation(c, username, users_index, by_conv.get(c["id"], [])) for c in mine]
    out.sort(key=lambda c: (c.last_message.created_at if c.last_message else c.created_at), reverse=True)
    return out


@router.post("/conversations", response_model=ChatConversationOut, status_code=status.HTTP_201_CREATED)
async def create_conversation(payload: ChatConversationCreate, user: dict = Depends(get_current_user)):
    username = user["username"]
    users_index = _users_by_username()
    targets = [u for u in dict.fromkeys(payload.member_usernames) if u != username]
    unknown = [u for u in targets if u not in users_index]
    if unknown:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown user(s): {', '.join(unknown)}")

    now = _now()

    if payload.type == "direct":
        if len(targets) != 1:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "A direct chat needs exactly one other user")
        other = targets[0]
        existing = next(
            (
                c
                for c in storage.read_all(storage.CHAT_CONVERSATIONS_FILE)
                if c["type"] == "direct" and set(_member_usernames(c)) == {username, other}
            ),
            None,
        )
        if existing:
            return _serialize_conversation(existing, username, users_index, _messages_for(existing["id"]))

        conv = {
            "id": str(uuid.uuid4()),
            "type": "direct",
            "name": None,
            "picture_url": None,
            "created_by": username,
            "created_at": now,
            "updated_at": now,
            "members": [
                {"username": username, "role": "admin", "joined_at": now, "last_read_at": now},
                {"username": other, "role": "admin", "joined_at": now, "last_read_at": None},
            ],
        }
    else:
        if not payload.name or not payload.name.strip():
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Groups need a name")
        if not targets:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Add at least one other member to the group")
        conv = {
            "id": str(uuid.uuid4()),
            "type": "group",
            "name": payload.name.strip(),
            "picture_url": None,
            "created_by": username,
            "created_at": now,
            "updated_at": now,
            "members": [{"username": username, "role": "admin", "joined_at": now, "last_read_at": now}]
            + [{"username": u, "role": "member", "joined_at": now, "last_read_at": None} for u in targets],
        }

    storage.append(storage.CHAT_CONVERSATIONS_FILE, conv)
    out = _serialize_conversation(conv, username, users_index, [])
    await manager.broadcast(_member_usernames(conv), {"event": "conversation.new", "conversation": out.model_dump()})
    return out


@router.get("/conversations/{conversation_id}", response_model=ChatConversationOut)
def get_conversation(conversation_id: str, user: dict = Depends(get_current_user)):
    conv = _get_conversation_or_404(conversation_id)
    _require_member(conv, user["username"])
    return _serialize_conversation(conv, user["username"], _users_by_username(), _messages_for(conversation_id))


@router.patch("/conversations/{conversation_id}", response_model=ChatConversationOut)
async def update_conversation(conversation_id: str, payload: ChatConversationUpdate, user: dict = Depends(get_current_user)):
    conv = _get_conversation_or_404(conversation_id)
    username = user["username"]
    _require_member(conv, username)
    if conv["type"] != "group":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only groups can be renamed or re-pictured")
    _require_admin(conv, username)

    updates: dict = {}
    if payload.name is not None:
        if not payload.name.strip():
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Group name can't be empty")
        updates["name"] = payload.name.strip()
    if payload.picture_url is not None:
        updates["picture_url"] = payload.picture_url
    if updates:
        updates["updated_at"] = _now()
        storage.update_one(storage.CHAT_CONVERSATIONS_FILE, "id", conversation_id, updates)
        conv = {**conv, **updates}

    out = _serialize_conversation(conv, username, _users_by_username(), _messages_for(conversation_id))
    await manager.broadcast(_member_usernames(conv), {"event": "conversation.updated", "conversation": out.model_dump()})
    return out


@router.post("/conversations/{conversation_id}/picture", response_model=ChatConversationOut)
async def upload_group_picture(conversation_id: str, file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    conv = _get_conversation_or_404(conversation_id)
    username = user["username"]
    _require_member(conv, username)
    if conv["type"] != "group":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only groups have a picture")
    _require_admin(conv, username)
    if not media.is_configured():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Media uploads aren't configured on this server yet")

    content_type = file.content_type or ""
    if not content_type.startswith("image/"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"'{file.filename}' isn't an image ({content_type or 'unknown type'})")
    content = await file.read()
    if len(content) > MAX_AVATAR_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, f"Image is {len(content) / 1_000_000:.1f}MB, max is 5MB")

    try:
        result = media.upload_file(content, file.filename or "group", content_type, folder="gt-chat-groups")
    except media.MediaUploadError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc

    now = _now()
    storage.update_one(storage.CHAT_CONVERSATIONS_FILE, "id", conversation_id, {"picture_url": result["url"], "updated_at": now})
    conv = {**conv, "picture_url": result["url"], "updated_at": now}
    out = _serialize_conversation(conv, username, _users_by_username(), _messages_for(conversation_id))
    await manager.broadcast(_member_usernames(conv), {"event": "conversation.updated", "conversation": out.model_dump()})
    return out


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(conversation_id: str, user: dict = Depends(get_current_user)):
    conv = _get_conversation_or_404(conversation_id)
    username = user["username"]
    _require_member(conv, username)
    if conv["type"] == "group":
        # Whole-group deletion is admin-only; regular members use the
        # "leave" action (DELETE .../members/{their own username}) instead.
        _require_admin(conv, username)
    # Direct chats: deleting removes it for both participants — this app
    # doesn't (yet) support hiding a chat for just one side.
    members = _member_usernames(conv)
    storage.delete_one(storage.CHAT_CONVERSATIONS_FILE, "id", conversation_id)
    storage.delete_many(storage.CHAT_MESSAGES_FILE, "conversation_id", {conversation_id})
    await manager.broadcast(members, {"event": "conversation.deleted", "conversation_id": conversation_id})
    return None


# ---------------------------------------------------------------------------
# Group membership
# ---------------------------------------------------------------------------

@router.post("/conversations/{conversation_id}/members", response_model=ChatConversationOut)
async def add_members(conversation_id: str, payload: ChatMembersAdd, user: dict = Depends(get_current_user)):
    conv = _get_conversation_or_404(conversation_id)
    username = user["username"]
    _require_member(conv, username)
    if conv["type"] != "group":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Can't add members to a direct chat")
    _require_admin(conv, username)

    users_index = _users_by_username()
    existing = set(_member_usernames(conv))
    to_add = [u for u in dict.fromkeys(payload.usernames) if u not in existing]
    unknown = [u for u in to_add if u not in users_index]
    if unknown:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown user(s): {', '.join(unknown)}")
    if not to_add:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Those users are already in the group")

    now = _now()
    new_members = conv["members"] + [{"username": u, "role": "member", "joined_at": now, "last_read_at": None} for u in to_add]
    storage.update_one(storage.CHAT_CONVERSATIONS_FILE, "id", conversation_id, {"members": new_members, "updated_at": now})
    conv = {**conv, "members": new_members, "updated_at": now}

    out = _serialize_conversation(conv, username, users_index, _messages_for(conversation_id))
    await manager.broadcast(_member_usernames(conv), {"event": "conversation.updated", "conversation": out.model_dump()})
    return out


@router.delete("/conversations/{conversation_id}/members/{target_username}")
async def remove_member(conversation_id: str, target_username: str, user: dict = Depends(get_current_user)):
    conv = _get_conversation_or_404(conversation_id)
    username = user["username"]
    _require_member(conv, username)
    if conv["type"] != "group":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Can't remove members from a direct chat — delete it instead")
    if target_username != username:
        _require_admin(conv, username)  # removing someone else requires admin; leaving yourself never does
    if target_username not in _member_usernames(conv):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not a member of this group")

    all_members_before = _member_usernames(conv)
    remaining = [m for m in conv["members"] if m["username"] != target_username]
    now = _now()

    if not remaining:
        storage.delete_one(storage.CHAT_CONVERSATIONS_FILE, "id", conversation_id)
        storage.delete_many(storage.CHAT_MESSAGES_FILE, "conversation_id", {conversation_id})
        await manager.broadcast(all_members_before, {"event": "conversation.deleted", "conversation_id": conversation_id})
        return {"conversation_id": conversation_id, "deleted": True}

    # A group can never be left without an admin — promote the
    # longest-standing remaining member if the last admin just left.
    if not any(m["role"] == "admin" for m in remaining):
        remaining[0] = {**remaining[0], "role": "admin"}

    storage.update_one(storage.CHAT_CONVERSATIONS_FILE, "id", conversation_id, {"members": remaining, "updated_at": now})
    conv = {**conv, "members": remaining, "updated_at": now}

    out = _serialize_conversation(conv, username, _users_by_username(), _messages_for(conversation_id))
    await manager.broadcast(all_members_before, {"event": "conversation.updated", "conversation": out.model_dump()})
    return out.model_dump()


@router.patch("/conversations/{conversation_id}/members/{target_username}", response_model=ChatConversationOut)
async def update_member_role(
    conversation_id: str, target_username: str, payload: ChatMemberRoleUpdate, user: dict = Depends(get_current_user)
):
    conv = _get_conversation_or_404(conversation_id)
    username = user["username"]
    _require_member(conv, username)
    if conv["type"] != "group":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Direct chats have no roles")
    _require_admin(conv, username)
    if target_username not in _member_usernames(conv):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not a member of this group")

    updated_members = [{**m, "role": payload.role} if m["username"] == target_username else m for m in conv["members"]]
    now = _now()
    storage.update_one(storage.CHAT_CONVERSATIONS_FILE, "id", conversation_id, {"members": updated_members, "updated_at": now})
    conv = {**conv, "members": updated_members, "updated_at": now}

    out = _serialize_conversation(conv, username, _users_by_username(), _messages_for(conversation_id))
    await manager.broadcast(_member_usernames(conv), {"event": "conversation.updated", "conversation": out.model_dump()})
    return out


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------

@router.get("/conversations/{conversation_id}/messages", response_model=list[ChatMessageOut])
def list_messages(
    conversation_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    before: str | None = Query(default=None, description="ISO timestamp cursor — returns the page just before this"),
    user: dict = Depends(get_current_user),
):
    conv = _get_conversation_or_404(conversation_id)
    _require_member(conv, user["username"])
    msgs = sorted(_messages_for(conversation_id), key=lambda m: m["created_at"])
    if before:
        msgs = [m for m in msgs if m["created_at"] < before]
    page = msgs[-limit:]
    return [_serialize_message(m, conv) for m in page]


@router.post("/conversations/{conversation_id}/messages", response_model=ChatMessageOut, status_code=status.HTTP_201_CREATED)
async def send_message(conversation_id: str, payload: ChatMessageCreate, user: dict = Depends(get_current_user)):
    conv = _get_conversation_or_404(conversation_id)
    username = user["username"]
    _require_member(conv, username)

    now = _now()
    msg = {
        "id": str(uuid.uuid4()),
        "conversation_id": conversation_id,
        "sender": username,
        "type": "text",
        "text": payload.text,
        "media_url": None,
        "media_type": None,
        "file_name": None,
        "created_at": now,
        "edited_at": None,
        "deleted": False,
    }
    storage.append(storage.CHAT_MESSAGES_FILE, msg)
    _touch_and_mark_read(conv, username, now)

    out = _serialize_message(msg, conv)
    await manager.broadcast(_member_usernames(conv), {"event": "message.new", "conversation_id": conversation_id, "message": out.model_dump()})
    return out


@router.post("/conversations/{conversation_id}/messages/media", response_model=ChatMessageOut, status_code=status.HTTP_201_CREATED)
async def send_media_message(
    conversation_id: str,
    file: UploadFile = File(...),
    caption: str | None = Form(default=None),
    user: dict = Depends(get_current_user),
):
    conv = _get_conversation_or_404(conversation_id)
    username = user["username"]
    _require_member(conv, username)
    if not media.is_configured():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Media uploads aren't configured on this server yet")

    content_type = file.content_type or "application/octet-stream"
    content = await file.read()
    if len(content) > MAX_CHAT_MEDIA_BYTES:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"File is {len(content) / 1_000_000:.1f}MB, max is {MAX_CHAT_MEDIA_BYTES // 1_000_000}MB",
        )

    try:
        result = media.upload_file(content, file.filename or "attachment", content_type, folder="gt-chat")
    except media.MediaUploadError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc

    if content_type.startswith("image/"):
        msg_type = "image"
    elif content_type.startswith("video/"):
        msg_type = "video"
    elif content_type.startswith("audio/"):
        msg_type = "audio"
    else:
        msg_type = "file"

    now = _now()
    msg = {
        "id": str(uuid.uuid4()),
        "conversation_id": conversation_id,
        "sender": username,
        "type": msg_type,
        "text": caption or None,
        "media_url": result["url"],
        "media_type": content_type,
        "file_name": file.filename,
        "created_at": now,
        "edited_at": None,
        "deleted": False,
    }
    storage.append(storage.CHAT_MESSAGES_FILE, msg)
    _touch_and_mark_read(conv, username, now)

    out = _serialize_message(msg, conv)
    await manager.broadcast(_member_usernames(conv), {"event": "message.new", "conversation_id": conversation_id, "message": out.model_dump()})
    return out


@router.patch("/messages/{message_id}", response_model=ChatMessageOut)
async def edit_message(message_id: str, payload: ChatMessageEdit, user: dict = Depends(get_current_user)):
    msg = _get_message_or_404(message_id)
    username = user["username"]
    conv = _get_conversation_or_404(msg["conversation_id"])
    _require_member(conv, username)
    if msg["sender"] != username:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only edit your own messages")
    if msg.get("deleted"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Can't edit a deleted message")
    if msg["type"] != "text":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only text messages can be edited (add a caption by resending media)")

    now = _now()
    storage.update_one(storage.CHAT_MESSAGES_FILE, "id", message_id, {"text": payload.text, "edited_at": now})
    msg = {**msg, "text": payload.text, "edited_at": now}

    out = _serialize_message(msg, conv)
    await manager.broadcast(
        _member_usernames(conv), {"event": "message.updated", "conversation_id": conv["id"], "message": out.model_dump()}
    )
    return out


@router.delete("/messages/{message_id}", response_model=ChatMessageOut)
async def delete_message(message_id: str, user: dict = Depends(get_current_user)):
    msg = _get_message_or_404(message_id)
    username = user["username"]
    conv = _get_conversation_or_404(msg["conversation_id"])
    _require_member(conv, username)
    if msg["sender"] != username:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only delete your own messages")

    updates = {"deleted": True, "text": None, "media_url": None}
    storage.update_one(storage.CHAT_MESSAGES_FILE, "id", message_id, updates)
    msg = {**msg, **updates}

    out = _serialize_message(msg, conv)
    await manager.broadcast(
        _member_usernames(conv), {"event": "message.deleted", "conversation_id": conv["id"], "message": out.model_dump()}
    )
    return out


@router.post("/conversations/{conversation_id}/read")
async def mark_conversation_read(conversation_id: str, user: dict = Depends(get_current_user)):
    conv = _get_conversation_or_404(conversation_id)
    username = user["username"]
    _require_member(conv, username)

    now = _now()
    updated_members = [{**m, "last_read_at": now} if m["username"] == username else m for m in conv["members"]]
    storage.update_one(storage.CHAT_CONVERSATIONS_FILE, "id", conversation_id, {"members": updated_members})

    await manager.broadcast(
        [u for u in _member_usernames(conv) if u != username],
        {"event": "conversation.read", "conversation_id": conversation_id, "username": username, "at": now},
    )
    return {"read_at": now}


# ---------------------------------------------------------------------------
# Live updates
# ---------------------------------------------------------------------------

@router.websocket("/ws")
async def chat_ws(websocket: WebSocket):
    """Browsers can't attach an Authorization header to a WebSocket
    handshake, so the access token travels as a query param instead
    (?token=...) — same JWT, just a different transport."""
    token = websocket.query_params.get("token")
    username = None
    if token:
        try:
            payload = security.decode_token_of_type(token, expected_type="access")
            username = payload.get("sub")
        except JWTError:
            username = None

    if not username:
        await websocket.close(code=4401)
        return

    await manager.connect(username, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("event") == "typing":
                conversation_id = data.get("conversation_id")
                conv = _get_conversation(conversation_id)
                if conv and username in _member_usernames(conv):
                    await manager.broadcast(
                        [u for u in _member_usernames(conv) if u != username],
                        {"event": "typing", "conversation_id": conversation_id, "username": username},
                    )
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        manager.disconnect(username, websocket)
