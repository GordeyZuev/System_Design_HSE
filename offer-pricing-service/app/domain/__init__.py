"""Domain layer."""
from app.domain.exceptions import (
    ConfigServiceUnavailableException,
    DomainException,
    InvalidOfferStateException,
    OfferAlreadyUsedException,
    OfferExpiredException,
    OfferNotFoundException,
    TariffNotFoundException,
    TariffServiceUnavailableException,
    UserServiceUnavailableException,
)
from app.domain.models import (
    ConfigData,
    CreateOfferRequest,
    CreateOfferResponse,
    GetOfferResponse,
    Offer,
    OfferStatus,
    TariffInfo,
    UserInfo,
    UserSegment,
)

__all__ = [
    # Models
    "Offer",
    "OfferStatus",
    "TariffInfo",
    "UserInfo",
    "UserSegment",
    "ConfigData",
    "CreateOfferRequest",
    "CreateOfferResponse",
    "GetOfferResponse",
    # Exceptions
    "DomainException",
    "OfferNotFoundException",
    "OfferExpiredException",
    "OfferAlreadyUsedException",
    "TariffNotFoundException",
    "TariffServiceUnavailableException",
    "UserServiceUnavailableException",
    "ConfigServiceUnavailableException",
    "InvalidOfferStateException",
]

