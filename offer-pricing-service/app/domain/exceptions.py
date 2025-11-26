"""Domain exceptions for Offer & Pricing Service."""


class DomainException(Exception):
    """Base domain exception."""

    def __init__(self, message: str, code: str = "DOMAIN_ERROR") -> None:
        self.message = message
        self.code = code
        super().__init__(self.message)


class OfferNotFoundException(DomainException):
    """Offer not found exception."""

    def __init__(self, offer_id: str) -> None:
        super().__init__(
            message=f"Offer with id {offer_id} not found",
            code="OFFER_NOT_FOUND",
        )


class OfferExpiredException(DomainException):
    """Offer expired exception."""

    def __init__(self, offer_id: str) -> None:
        super().__init__(
            message=f"Offer {offer_id} has expired",
            code="OFFER_EXPIRED",
        )


class OfferAlreadyUsedException(DomainException):
    """Offer already used exception."""

    def __init__(self, offer_id: str) -> None:
        super().__init__(
            message=f"Offer {offer_id} has already been used",
            code="OFFER_ALREADY_USED",
        )


class TariffNotFoundException(DomainException):
    """Tariff not found exception."""

    def __init__(self, station_id: str) -> None:
        super().__init__(
            message=f"Tariff for station {station_id} not found",
            code="TARIFF_NOT_FOUND",
        )


class TariffServiceUnavailableException(DomainException):
    """Tariff service unavailable exception."""

    def __init__(self) -> None:
        super().__init__(
            message="Tariff service is unavailable",
            code="TARIFF_SERVICE_UNAVAILABLE",
        )


class UserServiceUnavailableException(DomainException):
    """User service unavailable exception."""

    def __init__(self) -> None:
        super().__init__(
            message="User service is unavailable, using greedy pricing",
            code="USER_SERVICE_UNAVAILABLE",
        )


class ConfigServiceUnavailableException(DomainException):
    """Config service unavailable exception."""

    def __init__(self) -> None:
        super().__init__(
            message="Config service is unavailable",
            code="CONFIG_SERVICE_UNAVAILABLE",
        )


class InvalidOfferStateException(DomainException):
    """Invalid offer state exception."""

    def __init__(self, message: str) -> None:
        super().__init__(
            message=message,
            code="INVALID_OFFER_STATE",
        )

