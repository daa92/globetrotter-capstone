"""
app/routers/users.py

The user's self-service "portal": view profile, update profile fields
(including username and email, each with their own uniqueness/identity
concerns — see below), upload a profile picture, delete own account.
Every route here operates on the caller's own account only — there is
no username parameter, so there's no risk of a user editing someone
else's profile.
"""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app import audit, media, security, storage, username_rename
from app.dependencies import get_current_user
from app.schemas import AvatarUploadResponse, ProfileUpdateResponse, UserProfileUpdate, UserPublic

router = APIRouter(prefix="/users", tags=["users"])

MAX_AVATAR_BYTES = 5_000_000  # 5MB — a profile picture has no business being bigger than this


@router.get("/me", response_model=UserPublic)
def get_my_profile(user: dict = Depends(get_current_user)):
    return UserPublic(**user)


@router.patch("/me", response_model=ProfileUpdateResponse)
def update_my_profile(payload: UserProfileUpdate, user: dict = Depends(get_current_user)):
    updates = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    new_access_token = None
    old_username = user["username"]

    # Email is "one email used for one person" — enforce uniqueness on
    # every update, not just at registration, since nothing currently
    # stops two accounts from converging on the same address otherwise.
    if "email" in updates and updates["email"].lower() != (user.get("email") or "").lower():
        others = storage.read_all(storage.USERS_FILE)
        if any(u["username"] != old_username and (u.get("email") or "").lower() == updates["email"].lower() for u in others):
            raise HTTPException(status.HTTP_409_CONFLICT, "That email is already in use by another account")

    # Username rename is a much bigger operation (cascades across every
    # collection keyed by username — see app/username_rename.py) and
    # invalidates the caller's current access token, so it's handled
    # separately from the plain-field updates below.
    new_username = updates.pop("username", None)
    if new_username and new_username != old_username:
        try:
            user = username_rename.rename_username(old_username, new_username)
        except username_rename.UsernameTakenError as exc:
            raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
        new_access_token = security.create_access_token(new_username)
        audit.log_action(new_username, "user.renamed", target=new_username, details=f"was '{old_username}'")

    if updates:
        storage.update_one(storage.USERS_FILE, "username", user["username"], updates)
        user = {**user, **updates}

    return ProfileUpdateResponse(**user, access_token=new_access_token)


@router.post("/me/profile-picture", response_model=AvatarUploadResponse)
async def upload_profile_picture(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    if not media.is_configured():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Media uploads aren't configured on this server yet")

    content_type = file.content_type or ""
    if not content_type.startswith("image/"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"'{file.filename}' isn't an image ({content_type or 'unknown type'})")

    content = await file.read()
    if len(content) > MAX_AVATAR_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, f"Image is {len(content) / 1_000_000:.1f}MB, max is 5MB")

    try:
        result = media.upload_file(content, file.filename or "avatar", content_type, folder="gt-avatars")
    except media.MediaUploadError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc

    storage.update_one(storage.USERS_FILE, "username", user["username"], {"profile_picture_url": result["url"]})
    return AvatarUploadResponse(profile_picture_url=result["url"])


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_account(user: dict = Depends(get_current_user)):
    storage.delete_one(storage.USERS_FILE, "username", user["username"])
    # Also scrub the user's itineraries so no orphaned personal data lingers.
    itineraries = storage.read_all(storage.ITINERARIES_FILE)
    remaining = [it for it in itineraries if it.get("username") != user["username"]]
    storage.replace_all(storage.ITINERARIES_FILE, remaining)
    return None
