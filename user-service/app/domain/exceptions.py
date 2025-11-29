"""Domain exceptions for User Service."""


class DomainException(Exception):
    """Base domain exception."""

    def __init__(self, message: str, code: str = "DOMAIN_ERROR") -> None:
        self.message = message
        self.code = code
        super().__init__(self.message)


class UserNotFoundException(DomainException):
    """User not found exception."""

    def __init__(self, user_id: str = None, email: str = None) -> None:
        if user_id:
            message = f"User with id {user_id} not found"
        elif email:
            message = f"User with email {email} not found"
        else:
            message = "User not found"
        super().__init__(message=message, code="USER_NOT_FOUND")


class InvalidCredentialsException(DomainException):
    """Invalid credentials exception."""

    def __init__(self) -> None:
        super().__init__(
            message="Invalid email or password",
            code="INVALID_CREDENTIALS",
        )


class InvalidTokenException(DomainException):
    """Invalid token exception."""

    def __init__(self, message: str = "Invalid token") -> None:
        super().__init__(message=message, code="INVALID_TOKEN")


class TokenExpiredException(DomainException):
    """Token expired exception."""

    def __init__(self) -> None:
        super().__init__(
            message="Token has expired",
            code="TOKEN_EXPIRED",
        )


class RefreshTokenNotFoundException(DomainException):
    """Refresh token not found exception."""

    def __init__(self) -> None:
        super().__init__(
            message="Refresh token not found",
            code="REFRESH_TOKEN_NOT_FOUND",
        )


class RefreshTokenRevokedException(DomainException):
    """Refresh token revoked exception."""

    def __init__(self) -> None:
        super().__init__(
            message="Refresh token has been revoked",
            code="REFRESH_TOKEN_REVOKED",
        )

