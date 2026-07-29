"""
app/routers/auth.py

Registration, login (with optional MFA second factor), MFA enrollment,
token refresh via httpOnly cookie, and logout.

Auth flow:
  1. POST /auth/register            -> create account
  2. POST /auth/login               -> if MFA disabled: access token + refresh cookie
                                        if MFA enabled: {mfa_required: true}, no tokens yet
  3. POST /auth/login/mfa           -> username + password + code -> tokens
  4. POST /auth/mfa/setup           -> (authenticated) get QR provisioning URI
  5. POST /auth/mfa/confirm         -> (authenticated) confirm code, enable MFA
  6. POST /auth/refresh             -> read refresh cookie -> new access token
  7. POST /auth/logout              -> clear refresh cookie
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from jose import JWTError

from app import security, storage
from app.config import settings
from app.dependencies import get_current_user
from app.notifications import outbox
from app.schemas import (
    MFAConfirmRequest,
    MFALoginChallenge,
    MFASetupResponse,
    RegisterResponse,
    TokenResponse,
    UserLogin,
    UserRegister,
    VerifyRequest,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_refresh_cookie(response: Response, username: str) -> None:
    refresh_token = security.create_refresh_token(username)
    response.set_cookie(
        key=settings.COOKIE_NAME_REFRESH,
        value=refresh_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/auth",
    )


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister):
    users = storage.read_all(storage.USERS_FILE)
    if any(u["username"] == payload.username for u in users):
        raise HTTPException(status.HTTP_409_CONFLICT, "Username already taken")
    if any(u["email"] == payload.email for u in users):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")

    verification_token = str(uuid.uuid4())
    user = {
        "username": payload.username,
        "email": payload.email,
        "hashed_password": security.hash_password(payload.password),
        "preferences": payload.preferences,
        "profile_picture_url": None,
        "mfa_enabled": False,
        "mfa_secret": None,
        "is_admin": False,
        "is_verified": False,
        "verification_token": verification_token,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    storage.append(storage.USERS_FILE, user)

    outbox.send(
        to=payload.email,
        subject="Verify your GT account",
        body=(
            f"Welcome to GT! Verify your account within "
            f"{settings.UNVERIFIED_ACCOUNT_TTL_MINUTES} minutes using this token: "
            f"{verification_token}\n\n"
            f"(In production this would be a clickable link to "
            f"https://your-domain/verify?token={verification_token})"
        ),
    )

    return RegisterResponse(**user)


@router.post("/verify")
def verify_account(payload: VerifyRequest):
    users = storage.read_all(storage.USERS_FILE)
    user = next((u for u in users if u.get("verification_token") == payload.token), None)
    if not user:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or already-used verification token")
    if user.get("is_verified"):
        return {"detail": "Account already verified"}

    storage.update_one(
        storage.USERS_FILE, "username", user["username"],
        {"is_verified": True},
    )
    return {"detail": "Account verified — you can now log in."}


def _authenticate(username: str, password: str) -> dict:
    users = storage.read_all(storage.USERS_FILE)
    user = next((u for u in users if u["username"] == username), None)
    if not user or not security.verify_password(password, user["hashed_password"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid username or password")
    return user


@router.post("/login")
def login(payload: UserLogin, response: Response):
    user = _authenticate(payload.username, payload.password)

    if not user.get("is_verified", False):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Account not yet verified. Check your email for the verification token "
            f"(expires {settings.UNVERIFIED_ACCOUNT_TTL_MINUTES} minutes after registration).",
        )

    if user.get("mfa_enabled"):
        if not payload.mfa_code:
            # Password was correct but a second factor is required.
            return MFALoginChallenge(username=user["username"])
        if not security.verify_mfa_code(user["mfa_secret"], payload.mfa_code):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid MFA code")

    access_token = security.create_access_token(user["username"])
    _set_refresh_cookie(response, user["username"])
    return TokenResponse(
        access_token=access_token,
        expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    )


@router.post("/mfa/setup", response_model=MFASetupResponse)
def mfa_setup(user: dict = Depends(get_current_user)):
    """Generates a new TOTP secret. MFA is NOT enabled until /mfa/confirm succeeds."""
    secret = security.generate_mfa_secret()
    storage.update_one(storage.USERS_FILE, "username", user["username"], {"mfa_secret": secret})
    uri = security.get_mfa_provisioning_uri(secret, user["username"])
    return MFASetupResponse(secret=secret, provisioning_uri=uri)


@router.post("/mfa/confirm")
def mfa_confirm(payload: MFAConfirmRequest, user: dict = Depends(get_current_user)):
    if not user.get("mfa_secret"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Call /auth/mfa/setup first")
    if not security.verify_mfa_code(user["mfa_secret"], payload.code):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid code")
    storage.update_one(storage.USERS_FILE, "username", user["username"], {"mfa_enabled": True})
    return {"detail": "MFA enabled"}


@router.post("/mfa/disable")
def mfa_disable(user: dict = Depends(get_current_user)):
    storage.update_one(
        storage.USERS_FILE,
        "username",
        user["username"],
        {"mfa_enabled": False, "mfa_secret": None},
    )
    return {"detail": "MFA disabled"}


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    response: Response,
    gt_refresh_token: str | None = Cookie(default=None),
):
    """Reads the httpOnly refresh cookie set at login and issues a fresh
    access token, rotating the refresh token in the process."""
    token = gt_refresh_token
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing refresh token")
    try:
        payload = security.decode_token_of_type(token, expected_type="refresh")
    except JWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired refresh token")

    username = payload["sub"]
    access_token = security.create_access_token(username)
    _set_refresh_cookie(response, username)  # rotate refresh token
    return TokenResponse(access_token=access_token, expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(settings.COOKIE_NAME_REFRESH, path="/auth")
    return {"detail": "Logged out"}
