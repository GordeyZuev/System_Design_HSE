"""Domain exceptions for Rental Command Service."""


class DomainException(Exception):
    """Base domain exception."""

    def __init__(self, message: str, code: str = "DOMAIN_ERROR") -> None:
        self.message = message
        self.code = code
        super().__init__(self.message)


class OfferNotActiveException(DomainException):
    """Offer not active exception."""

    def __init__(self, offer_id: str) -> None:
        super().__init__(
            message=f"Offer with id {offer_id} not found",
            code="OFFER_NOT_ACTIVE",
        )


class ExpireAtNotFoundException(DomainException):
    """Offer not found expire_at exception."""

    def __init__(self, offer_id: str) -> None:
        super().__init__(
            message=f"No expire_at field for {offer_id} offer",
            code="EXPIRE_AT_NOT_FOUND",
        )


class UserAlreadyRentException(DomainException):
    """User already has active rent exception."""

    def __init__(self, user_id: str, offer_id: str) -> None:
        super().__init__(
            message=f"User {user_id} already have active offer, offer_id = {offer_id}",
            code="USER_ALREADY_ACTIVE",
        )


class OfferNotBelongUserException(DomainException):
    """Offer does not belong to this user"""

    def __init__(self, user_id: str, offer_id: str) -> None:
        super().__init__(
            message=f"Offer {offer_id} does not belong to this user {user_id}",
            code="OFFER_USER_MISMATCH",
        )


class OfferExpiredException(DomainException):
    """Offer expired"""

    def __init__(self, offer_id: str) -> None:
        super().__init__(
            message=f"Offer {offer_id} expired",
            code="OFFER_EXPIRED",
        )


class StationIdMissedException(DomainException):
    """Missed station_id field"""

    def __init__(self, offer_id: str) -> None:
        super().__init__(
            message=f"Offer {offer_id} doesn't contain station_id field ",
            code="STATION_ID_FIELD",
        )


class RentalNotFoundException(DomainException):
    """Rental not found"""

    def __init__(self, user_id: str, rental_id: str) -> None:
        super().__init__(
            message=f"Rental {rental_id} not found. user_id = {user_id}",
            code="RENTAL_NOT_FOUND",
        )


class RentalAlreadyFinishedException(DomainException):
    """Rental already finished"""

    def __init__(self, user_id: str, rental_id: str) -> None:
        super().__init__(
            message=f"Rental {rental_id} already finished. user_id = {user_id}",
            code="RENTAL_ALREADY_FINISHED",
        )


class UserIdsMismatchException(DomainException):
    """User_id from rentals and given user_id mismatched"""

    def __init__(self, user_id_rental: str, given_id: str) -> None:
        super().__init__(
            message=f"User_id {user_id_rental} from rentals and given user_id {given_id} mismatched",
            code="USER_IDS_MISMATCH",
        )
