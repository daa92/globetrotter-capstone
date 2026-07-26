"""
app/security.py

All cryptographic/security primitives live here so there is exactly one
place to audit: password hashing, JWT access/refresh tokens, and MFA
(TOTP) secret generation + verification.
"""
import uuid
from datetime import datetime, timedelta, timezone

import pyotp
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ---------------------------------------------------------------------------
# Passwords
# ---------------------------------------------------------------------------

def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# ---------------------------------------------------------------------------
# JWT — short-lived access token (sent in Authorization header) +
#       longer-lived refresh token (sent as an httpOnly, secure cookie)
# ---------------------------------------------------------------------------

def _create_token(subject: str, expires_delta: timedelta, token_type: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
        "jti": str(uuid.uuid4()),  # unique id, enables future revocation/blacklisting
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(username: str) -> str:
    return _create_token(
        username,
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        token_type="access",
    )


def create_refresh_token(username: str) -> str:
    return _create_token(
        username,
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        token_type="refresh",
    )


def decode_token(token: str) -> dict:
    """Raises jose.JWTError if invalid/expired. Caller must handle it."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


def decode_token_of_type(token: str, expected_type: str) -> dict:
    payload = decode_token(token)
    if payload.get("type") != expected_type:
        raise JWTError(f"Expected a {expected_type} token")
    return payload


# ---------------------------------------------------------------------------
# MFA — TOTP (Google Authenticator / Authy compatible)
# ---------------------------------------------------------------------------

def generate_mfa_secret() -> str:
    return pyotp.random_base32()


def get_mfa_provisioning_uri(secret: str, username: str) -> str:
    return pyotp.totp.TOTP(secret).provisioning_uri(
        name=username, issuer_name=settings.MFA_ISSUER_NAME
    )


def verify_mfa_code(secret: str, code: str) -> bool:
    return pyotp.totp.TOTP(secret).verify(code, valid_window=1)
