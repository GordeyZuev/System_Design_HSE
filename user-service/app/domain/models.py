"""Domain models for User Service."""
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class UserSegment(str, Enum):
    """User segment enum."""

    STANDARD = "STANDARD"
    PREMIUM = "PREMIUM"
    VIP = "VIP"


class UserStatus(str, Enum):
    """User status enum."""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    BLOCKED = "BLOCKED"


class User(BaseModel):
    """User domain model."""

    user_id: UUID = Field(default_factory=uuid4)
    email: str
    phone: Optional[str] = None
    password_hash: str
    status: UserStatus = UserStatus.ACTIVE
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"from_attributes": True}


class UserProfile(BaseModel):
    """User profile domain model."""

    user_id: UUID
    name: Optional[str] = None
    extra_metadata_json: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"from_attributes": True}


class UserSegmentModel(BaseModel):
    """User segment domain model."""

    user_id: UUID
    segment: UserSegment = UserSegment.STANDARD
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"from_attributes": True}


class RefreshToken(BaseModel):
    """Refresh token domain model."""

    token_id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    expires_at: datetime
    revoked: bool = False

    model_config = {"from_attributes": True}


class UserInfo(BaseModel):
    """User information response model."""

    user_id: UUID
    email: str
    segment: UserSegment
    status: str
    phone: Optional[str] = None


class LoginRequest(BaseModel):
    """Login request model."""

    email: str
    password: str


class LoginResponse(BaseModel):
    """Login response model."""

    access_token: str
    refresh_token: str
    user_id: UUID


class RefreshRequest(BaseModel):
    """Refresh token request model."""

    refresh_token: str


class RefreshResponse(BaseModel):
    """Refresh token response model."""

    access_token: str
    refresh_token: str


class JWTValidateRequest(BaseModel):
    """JWT validation request model."""

    token: str


class JWTValidateResponse(BaseModel):
    """JWT validation response model."""

    valid: bool
    user_id: Optional[UUID] = None
    segment: Optional[UserSegment] = None
    roles: Optional[List[str]] = None

