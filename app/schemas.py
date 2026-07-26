"""
app/schemas.py

Pydantic models = request validation + response contracts + free OpenAPI
docs. Nothing gets in or out of the API without matching one of these.
"""
from datetime import date
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class UserRegister(BaseModel):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[a-zA-Z0-9_.-]+$")
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    preferences: list[str] = Field(default_factory=list)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        if not any(c.isalpha() for c in v):
            raise ValueError("Password must contain at least one letter")
        return v


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


# ---------------------------------------------------------------------------
# Users / profile
# ---------------------------------------------------------------------------

class UserPublic(BaseModel):
    username: str
    email: EmailStr
    preferences: list[str] = Field(default_factory=list)
    profile_picture_url: Optional[str] = None
    mfa_enabled: bool = False
    created_at: str


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
