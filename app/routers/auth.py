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
import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from google.auth.exceptions import GoogleAuthError
from jose import JWTError

from app import security, storage
from app.config import settings
from app.dependencies import get_current_user
from app.google_oauth import verify_google_id_token
from app.notifications import outbox
from app.notifications.service import create_notification
from app.schemas import (
    GoogleAuthRequest,
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

    sponsor = None
    if payload.referral_code:
        sponsor = next((u for u in users if u["referral_code"] == payload.referral_code), None)
        if not sponsor:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid referral code")
        # Note: no separate "can't refer yourself" check needed here — the
        # username-uniqueness check above already guarantees payload.username
        # can't match an existing user's (the sponsor's) username.

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
        "referral_code": uuid.uuid4().hex[:8].upper(),
        "referred_by": sponsor["username"] if sponsor else None,
        "google_sub": None,
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

    # Credit the sponsor now, not at registration — an unverified referral
    # would just get deleted by the 30-minute cleanup job anyway, so this
    # is also the natural anti-abuse gate against fake referral signups.
    if user.get("referred_by"):
        storage.append(storage.REFERRALS_FILE, {
            "sponsor_username": user["referred_by"],
            "referred_username": user["username"],
            "amount_usd": settings.REFERRAL_BONUS_USD,
            "credited_at": datetime.now(timezone.utc).isoformat(),
        })
        create_notification(
            username=user["referred_by"],
            title="You earned a referral bonus!",
            message=f"{user['username']} just verified their account using your referral link — you earned ${settings.REFERRAL_BONUS_USD}.",
            category="referral",
        )
    return {"detail": "Account verified — you can now log in."}


def _authenticate(username: str, password: str) -> dict:
    users = storage.read_all(storage.USERS_FILE)
    user = next((u for u in users if u["username"] == username), None)
    # A Google-only account (created via /auth/google, never set a local
    # password) has hashed_password=None. Treat that the same as a wrong
    # password — a generic "invalid credentials" message, so this endpoint
    # never confirms/denies whether an account exists or how it was created.
    if not user or not user.get("hashed_password") or not security.verify_password(password, user["hashed_password"]):
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


def _generate_username_from_email(email: str, existing_users: list[dict]) -> str:
    """Derives a username candidate from the email's local part, sanitized
    to fit our username pattern, with a numeric suffix if it collides."""
    base = re.sub(r"[^a-zA-Z0-9_.-]", "", email.split("@")[0]) or "user"
    existing_usernames = {u["username"] for u in existing_users}
    candidate = base
    suffix = 1
    while candidate in existing_usernames:
        candidate = f"{base}{suffix}"
        suffix += 1
    return candidate


@router.post("/google")
def google_login(payload: GoogleAuthRequest, response: Response):
    """Sign in (or register, on first use) with Google. Only ever needs the
    Client ID — verification is a signature check against Google's public
    keys, not a secret exchange. New accounts are auto-verified (Google
    already confirmed the email), so the 30-minute unverified-account
    cleanup doesn't apply to them."""
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "Google sign-in is not configured on this server")

    try:
        google_payload = verify_google_id_token(payload.id_token)
    except ValueError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Invalid Google token: {exc}")
    except GoogleAuthError as exc:
        # Distinct from an invalid token: this means we couldn't even reach
        # Google to check it (network hiccup, cert endpoint down, etc.) —
        # worth a different status so a client/monitoring can tell "your
        # token is bad" apart from "try again in a moment".
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, f"Could not verify with Google right now: {exc}")

    if not google_payload.get("email_verified", False):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Google account email is not verified")

    email = google_payload["email"]
    google_sub = google_payload["sub"]

    users = storage.read_all(storage.USERS_FILE)
    user = next((u for u in users if u["email"] == email), None)

    if user is None:
        username = _generate_username_from_email(email, users)
        user = {
            "username": username,
            "email": email,
            "hashed_password": None,  # Google-only account until they set a local password
            "preferences": [],
            "profile_picture_url": google_payload.get("picture"),
            "mfa_enabled": False,
            "mfa_secret": None,
            "is_admin": False,
            "is_verified": True,  # Google already verified this email
            "verification_token": None,
            "referral_code": uuid.uuid4().hex[:8].upper(),
            "referred_by": None,
            "google_sub": google_sub,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        storage.append(storage.USERS_FILE, user)
    elif not user.get("google_sub"):
        # Existing local-password account signing in with Google for the
        # first time, same email — link the two rather than duplicate.
        storage.update_one(storage.USERS_FILE, "username", user["username"], {"google_sub": google_sub})
        user["google_sub"] = google_sub

    if user.get("mfa_enabled"):
        if not payload.mfa_code:
            return MFALoginChallenge(username=user["username"])
        if not security.verify_mfa_code(user["mfa_secret"], payload.mfa_code):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid MFA code")

    access_token = security.create_access_token(user["username"])
    _set_refresh_cookie(response, user["username"])
    return TokenResponse(access_token=access_token, expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
