"""
app/routers/users.py

The user's self-service "portal": view profile, update profile fields,
delete own account. Every route here operates on the caller's own
account only — there is no username parameter, so there's no risk of a
user editing someone else's profile.
"""
from fastapi import APIRouter, Depends, status

from app import storage
from app.dependencies import get_current_user
from app.schemas import UserProfileUpdate, UserPublic

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserPublic)
def get_my_profile(user: dict = Depends(get_current_user)):
    return UserPublic(**user)


@router.patch("/me", response_model=UserPublic)
def update_my_profile(payload: UserProfileUpdate, user: dict = Depends(get_current_user)):
    updates = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    if updates:
        storage.update_one(storage.USERS_FILE, "username", user["username"], updates)
        user = {**user, **updates}
    return UserPublic(**user)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_account(user: dict = Depends(get_current_user)):
    storage.delete_one(storage.USERS_FILE, "username", user["username"])
    # Also scrub the user's itineraries so no orphaned personal data lingers.
    itineraries = storage.read_all(storage.ITINERARIES_FILE)
    remaining = [it for it in itineraries if it.get("username") != user["username"]]
    storage.replace_all(storage.ITINERARIES_FILE, remaining)
    return None
