"""Domain models for Offer & Pricing Service."""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class OfferStatus(str, Enum):
    """Offer status enum."""

    ACTIVE = "ACTIVE"
    USED = "USED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class UserSegment(str, Enum):
    """User segment enum."""

    STANDARD = "STANDARD"
    PREMIUM = "PREMIUM"
    VIP = "VIP"


class Offer(BaseModel):
    """Offer domain model."""

    offer_id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    station_id: str
    tariff_snapshot: Dict[str, Any]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
    status: OfferStatus = OfferStatus.ACTIVE
    tariff_version: Optional[str] = None

    class Config:
        """Pydantic config."""

        from_attributes = True


class TariffInfo(BaseModel):
    """Tariff information model."""

    tariff_id: str
    station_id: str
    base_rate: float  # Base rate per minute
    segment_multiplier: float = 1.0
    currency: str = "RUB"
    version: str
    rules: Dict[str, Any] = Field(default_factory=dict)


class UserInfo(BaseModel):
    """User information model."""

    user_id: UUID
    segment: UserSegment = UserSegment.STANDARD
    status: str = "ACTIVE"
    email: Optional[str] = None


class ConfigData(BaseModel):
    """Configuration data model."""

    offer_ttl: int = 300  # seconds
    max_offers_per_user: int = 5
    pricing_rules: Dict[str, Any] = Field(default_factory=dict)


class CreateOfferRequest(BaseModel):
    """Request to create an offer."""

    user_id: UUID
    station_id: str
    user_segment: Optional[UserSegment] = None


class CreateOfferResponse(BaseModel):
    """Response after creating an offer."""

    offer_id: UUID
    expires_at: datetime
    tariff_details: Dict[str, Any]
    estimated_rate_per_minute: float
    currency: str = "RUB"


class GetOfferResponse(BaseModel):
    """Response for getting an offer."""

    offer_id: UUID
    user_id: UUID
    station_id: str
    status: OfferStatus
    created_at: datetime
    expires_at: datetime
    tariff_snapshot: Dict[str, Any]
    is_valid: bool

