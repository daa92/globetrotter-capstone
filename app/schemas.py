"""
app/schemas.py

Pydantic models = request validation + response contracts + free OpenAPI
docs. Nothing gets in or out of the API without matching one of these.
"""
from datetime import date
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


def _check_password_strength(v: str) -> str:
    if not any(c.isdigit() for c in v):
        raise ValueError("Password must contain at least one digit")
    if not any(c.isalpha() for c in v):
        raise ValueError("Password must contain at least one letter")
    return v


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class UserRegister(BaseModel):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[a-zA-Z0-9_.-]+$")
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    preferences: list[str] = Field(default_factory=list)
    referral_code: Optional[str] = Field(default=None, description="Referral code of the user who invited you, if any")

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _check_password_strength(v)


class PhoneRegister(BaseModel):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[a-zA-Z0-9_.-]+$", description="Your pseudo/display name")
    phone: str = Field(pattern=r"^\+?\d{8,15}$", description="e.g. +237650000000")
    password: str = Field(min_length=8, max_length=128)
    preferences: list[str] = Field(default_factory=list)
    referral_code: Optional[str] = Field(default=None)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _check_password_strength(v)


class UserLogin(BaseModel):
    username: str
    password: str
    mfa_code: Optional[str] = Field(default=None, description="Required only if MFA is enabled")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int


class MFASetupResponse(BaseModel):
    secret: str
    provisioning_uri: str
    note: str = "Scan provisioning_uri with an authenticator app, then confirm via /auth/mfa/confirm"


class MFAConfirmRequest(BaseModel):
    code: str = Field(min_length=6, max_length=6)


class MFALoginChallenge(BaseModel):
    mfa_required: bool = True
    username: str


class GoogleAuthRequest(BaseModel):
    id_token: str = Field(description="The credential/ID token from Google's Sign In button")
    mfa_code: Optional[str] = Field(default=None, description="Required only if the linked account has MFA enabled")


# ---------------------------------------------------------------------------
# Users / profile
# ---------------------------------------------------------------------------

class UserPublic(BaseModel):
    username: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    preferences: list[str] = Field(default_factory=list)
    profile_picture_url: Optional[str] = None
    mfa_enabled: bool = False
    is_verified: bool = False
    referral_code: str
    created_at: str


class VerifyRequest(BaseModel):
    token: str


class PasswordResetRequest(BaseModel):
    username: str


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _check_password_strength(v)


class RegisterResponse(UserPublic):
    detail: str = "Account created. Check your email for a verification link — it expires in 30 minutes."


class PhoneRegisterResponse(UserPublic):
    detail: str = "Account created. Check your SMS for a verification code — it expires in 30 minutes."


class UserProfileUpdate(BaseModel):
    email: Optional[EmailStr] = None
    preferences: Optional[list[str]] = None
    profile_picture_url: Optional[str] = None


# ---------------------------------------------------------------------------
# Destinations / places
# ---------------------------------------------------------------------------

class Destination(BaseModel):
    id: str
    name: str
    region: str
    tags: list[str] = Field(default_factory=list)
    description: str
    image_url: str
    latitude: float
    longitude: float
    avg_cost_fcfa: Optional[int] = None
    submitted_by: Optional[str] = None  # None = official seed data


class PlaceSubmission(BaseModel):
    name: str
    region: str
    tags: list[str] = Field(default_factory=list)
    description: str = Field(min_length=20, max_length=2000)
    image_url: str
    latitude: float = Field(ge=1.5, le=13.5, description="Rough Cameroon latitude bounds")
    longitude: float = Field(ge=8.0, le=16.5, description="Rough Cameroon longitude bounds")
    avg_cost_fcfa: Optional[int] = Field(default=None, ge=0)


# ---------------------------------------------------------------------------
# Itineraries
# ---------------------------------------------------------------------------

class ItineraryCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    destinations: list[str]
    start_date: date
    end_date: date

    @field_validator("end_date")
    @classmethod
    def end_after_start(cls, v: date, info):
        start = info.data.get("start_date")
        if start and v < start:
            raise ValueError("end_date must be on or after start_date")
        return v


class Itinerary(ItineraryCreate):
    id: str
    username: str
    created_at: str


# ---------------------------------------------------------------------------
# Feedback
# ---------------------------------------------------------------------------

class FeedbackCreate(BaseModel):
    category: str = Field(description="bug | suggestion | place_report | other")
    message: str = Field(min_length=5, max_length=2000)
    rating: Optional[int] = Field(default=None, ge=1, le=5)


# ---------------------------------------------------------------------------
# Earnings / referrals / payouts
# ---------------------------------------------------------------------------

class HeartbeatRequest(BaseModel):
    elapsed_seconds: int = Field(ge=1, le=3600, description="Seconds active since the last heartbeat")


class DailyActivity(BaseModel):
    date: str
    active_seconds: int
    qualified: bool  # met the daily usage threshold


class RequirementStatus(BaseModel):
    met: bool
    have: float
    need: float


class PayoutEligibility(BaseModel):
    eligible: bool
    balance: RequirementStatus
    referrals: RequirementStatus
    good_feedback: RequirementStatus
    has_pending_payout: bool


class EarningsResponse(BaseModel):
    qualifying_days: int
    usage_earnings_usd: float
    referral_count: int
    referral_earnings_usd: float
    good_feedback_count: int
    total_earned_usd: float
    total_paid_out_usd: float
    available_usd: float
    available_fcfa: float
    fcfa_rate: float
    referral_code: str
    referral_link: str
    today_active_seconds: int
    today_threshold_seconds: int
    daily_log: list[DailyActivity]
    payout_eligibility: PayoutEligibility


class PayoutRequestResult(BaseModel):
    id: str
    amount_usd: float
    amount_fcfa: float
    status: str
    requested_at: str


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

class NotificationOut(BaseModel):
    id: str
    title: str
    message: str
    category: str
    is_read: bool
    sent_by: str
    created_at: str


class NotificationBatchAction(BaseModel):
    ids: Optional[list[str]] = Field(default=None, description="Specific notification IDs")
    all: bool = Field(default=False, description="Apply to every one of your notifications")


class AdminSendNotificationRequest(BaseModel):
    usernames: Optional[list[str]] = Field(default=None, description="Target usernames; omit if broadcast=true")
    broadcast: bool = Field(default=False, description="Send to every user instead of specific usernames")
    title: str = Field(min_length=1, max_length=150)
    message: str = Field(min_length=1, max_length=2000)
    also_email: bool = Field(default=False, description="Also send via email if the user has one on file")
