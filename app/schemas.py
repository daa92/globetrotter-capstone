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
    # Without these, the frontend's `user.is_admin` / hidden admin-dashboard
    # route check was always false for everyone, admins included — this
    # model is what /users/me actually serializes through.
    is_admin: bool = False
    is_principal_admin: bool = False
    admin_permissions: list[str] = Field(default_factory=list)
    is_locked: bool = False


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
    username: Optional[str] = Field(default=None, min_length=3, max_length=32, pattern=r"^[a-zA-Z0-9_.-]+$")
    email: Optional[EmailStr] = None
    preferences: Optional[list[str]] = None
    profile_picture_url: Optional[str] = None


class ProfileUpdateResponse(UserPublic):
    # Only set when the username actually changed — the old access token
    # embeds the old username as its subject, so it stops resolving to
    # any account the moment the rename happens. The frontend must swap
    # in this new token immediately or the user is silently logged out
    # by their own edit.
    access_token: Optional[str] = None


class AvatarUploadResponse(BaseModel):
    profile_picture_url: str


# ---------------------------------------------------------------------------
# Destinations / places
# ---------------------------------------------------------------------------

class PriceListItem(BaseModel):
    item: str = Field(max_length=120)
    price_fcfa: int = Field(ge=0)


class Destination(BaseModel):
    id: str
    name: str
    region: str
    tags: list[str] = Field(default_factory=list)
    description: str  # primary/default-language description
    description_translations: dict[str, str] = Field(
        default_factory=dict, description="Extra language versions, e.g. {'fr': '...'}. Primary `description` is the fallback for any language not present here."
    )
    image_url: str  # primary/cover image — kept for backward compatibility
    latitude: float
    longitude: float
    avg_cost_fcfa: Optional[int] = None
    price_list: list[PriceListItem] = Field(default_factory=list)
    submitted_by: Optional[str] = None  # None = official seed data

    # --- Content enrichment (see app/enrichment.py) ---
    images: list[str] = Field(default_factory=list, description="Gallery — includes image_url plus any enriched photos")
    video_url: Optional[str] = None
    wiki_url: Optional[str] = None
    kinds: list[str] = Field(default_factory=list, description="POI categories from OpenTripMap, e.g. 'natural', 'beaches'")
    rating: Optional[float] = Field(default=None, description="0-5, from OpenTripMap's notability score — NOT a crowd rating, see enrichment.py")
    how_to_get_there: Optional[dict] = None
    enrichment_sources: list[str] = Field(default_factory=list)
    enriched_at: Optional[str] = None

    # --- First-party engagement (genuine GT user data, not external) ---
    likes: int = 0
    dislikes: int = 0


class PlaceSubmission(BaseModel):
    name: str
    region: str
    tags: list[str] = Field(default_factory=list)
    description: str = Field(min_length=20, max_length=2000)
    latitude: float = Field(ge=1.5, le=13.5, description="Rough Cameroon latitude bounds")
    longitude: float = Field(ge=8.0, le=16.5, description="Rough Cameroon longitude bounds")
    avg_cost_fcfa: Optional[int] = Field(default=None, ge=0)
    price_list: list[PriceListItem] = Field(default_factory=list, description="Individual priced items/products, e.g. menu prices")
    # Media is optional ("images/videos/both/nothing") and comes from
    # POST /places/upload-media, called before this — this endpoint just
    # takes the resulting URLs, it never receives raw file bytes itself.
    images: list[str] = Field(default_factory=list)
    video_url: Optional[str] = None


class PlaceUpdate(BaseModel):
    """Same shape as PlaceSubmission but every field optional — PATCH
    semantics, only supplied fields change.

    `description` + `description_language` work together: if
    `description_language` is omitted (or equals the primary language,
    "en"), `description` replaces the primary description as before. If
    `description_language` is set to something else (e.g. "fr"), the
    text is stored as a *translation* instead — the primary description
    is untouched, and `description_translations[language]` is set. This
    is how you can add a French translation without overwriting the
    original text.
    """
    name: Optional[str] = None
    region: Optional[str] = None
    tags: Optional[list[str]] = None
    description: Optional[str] = Field(default=None, min_length=20, max_length=2000)
    description_language: Optional[str] = Field(default=None, description="ISO 639-1 code, e.g. 'fr'. Omit or 'en' to edit the primary description.")
    latitude: Optional[float] = Field(default=None, ge=1.5, le=13.5)
    longitude: Optional[float] = Field(default=None, ge=8.0, le=16.5)
    avg_cost_fcfa: Optional[int] = Field(default=None, ge=0)
    price_list: Optional[list[PriceListItem]] = None
    images: Optional[list[str]] = None
    video_url: Optional[str] = None


class AdminDestinationUpdate(BaseModel):
    """Direct admin edit of ANY destination — including official seed
    data that never went through a place submission at all, and places
    submitted by other users. Deliberately separate from PlaceUpdate:
    PlaceUpdate operates on a PLACES_FILE submission record (owner-or-
    admin, with the "edit reverts to pending" rule for non-admins);
    this operates directly on the published DESTINATIONS_FILE record
    and is admin-only, no approval concept involved."""
    name: Optional[str] = None
    region: Optional[str] = None
    tags: Optional[list[str]] = None
    description: Optional[str] = Field(default=None, min_length=20, max_length=2000)
    description_language: Optional[str] = Field(default=None, description="ISO 639-1 code, e.g. 'fr'. Omit or 'en' to edit the primary description.")
    latitude: Optional[float] = Field(default=None, ge=1.5, le=13.5)
    longitude: Optional[float] = Field(default=None, ge=8.0, le=16.5)
    avg_cost_fcfa: Optional[int] = Field(default=None, ge=0)
    price_list: Optional[list[PriceListItem]] = None
    images: Optional[list[str]] = None
    video_url: Optional[str] = None


class MediaUploadResponse(BaseModel):
    images: list[str] = Field(default_factory=list)
    video_url: Optional[str] = None
    total_bytes: int


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


class AdminBootstrapRequest(BaseModel):
    username: str = Field(min_length=1, description="Existing account to promote to admin")
    secret: str = Field(min_length=1, description="Must match ADMIN_BOOTSTRAP_SECRET env var")


# ---------------------------------------------------------------------------
# Admin management (principal-admin only: promote/revoke other admins,
# grant/retrieve specific privileges)
# ---------------------------------------------------------------------------

class AdminUserOut(BaseModel):
    username: str
    email: Optional[EmailStr] = None
    is_principal_admin: bool
    admin_permissions: list[str]
    promoted_at: Optional[str] = None


class AdminPromoteRequest(BaseModel):
    permissions: list[str] = Field(
        default_factory=list,
        description="Subset of the grantable admin permissions to start this admin with",
    )


class AdminPermissionsUpdate(BaseModel):
    permissions: list[str] = Field(description="Full replacement list of this admin's permissions")


class NotificationBatchOut(BaseModel):
    id: str
    title: str
    message: str
    audience: str  # unicast | multicast | broadcast
    recipient_count: int
    sent_by: str
    also_email: bool
    emailed_count: int
    created_at: str


class UserSearchResult(BaseModel):
    username: str
    email: Optional[EmailStr] = None
    is_admin: bool


# ---------------------------------------------------------------------------
# Admin: full user directory + lock/unlock/delete (any admin with the
# "users" permission; locking/deleting an admin account is principal-only)
# ---------------------------------------------------------------------------

class AdminUserDetail(BaseModel):
    username: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    is_verified: bool
    is_locked: bool
    is_admin: bool
    is_principal_admin: bool
    admin_permissions: list[str] = Field(default_factory=list)
    mfa_enabled: bool
    created_at: str
    referral_code: str


class AdminLockRequest(BaseModel):
    reason: Optional[str] = Field(default=None, max_length=500)


# ---------------------------------------------------------------------------
# Admin: audit log + system overview
# ---------------------------------------------------------------------------

class AuditLogEntry(BaseModel):
    id: str
    actor: str
    action: str
    target: Optional[str] = None
    details: Optional[str] = None
    created_at: str


class SystemOverview(BaseModel):
    total_users: int
    verified_users: int
    unverified_users: int
    locked_users: int
    total_admins: int
    pending_payouts: int
    approved_payouts_total_usd: float
    pending_place_submissions: int
    total_feedback: int
    average_feedback_rating: Optional[float]
    notifications_sent_last_7d: int
    new_registrations_last_7d: int
    background_jobs: list[dict]


# ---------------------------------------------------------------------------
# Content enrichment + first-party voting (see app/enrichment.py)
# ---------------------------------------------------------------------------

class EnrichmentResult(BaseModel):
    destination_id: str
    updated_fields: list[str]
    sources_used: list[str]
    destination: Destination


class VoteResponse(BaseModel):
    destination_id: str
    likes: int
    dislikes: int
    your_vote: Optional[str] = None  # "like" | "dislike" | None


class CommentCreate(BaseModel):
    message: str = Field(min_length=1, max_length=1000)


class CommentOut(BaseModel):
    id: str
    destination_id: str
    username: str
    message: str
    created_at: str


# ---------------------------------------------------------------------------
# Trip routing (see app/geo_service.py's get_multi_route, app/transport_companies.py)
# ---------------------------------------------------------------------------

class RouteRequest(BaseModel):
    destination_ids: list[str] = Field(min_length=1, description="Ordered stops, in visiting order")
    start_lat: Optional[float] = Field(default=None, description="Trip starting point — your location or a chosen city. Omit to start from the reference city (Douala).")
    start_lng: Optional[float] = None
    start_label: Optional[str] = Field(default=None, description="Display label for the start point, e.g. 'Your location' or 'Douala'")


class RouteStop(BaseModel):
    name: str
    latitude: float
    longitude: float


class TransportSuggestion(BaseModel):
    name: str
    type: str  # "ride_hailing" | "bus" | "train"
    coverage: str
    best_for: str
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    note: Optional[str] = None


class RouteResponse(BaseModel):
    stops: list[RouteStop]
    total_distance_km: float
    total_duration_minutes: Optional[float] = None
    geometry: list[list[float]] = Field(default_factory=list, description="[[lat, lng], ...] polyline points — empty if only a straight-line fallback was available")
    method: str  # "driving" | "straight_line"
    transport_suggestions: list[TransportSuggestion]

