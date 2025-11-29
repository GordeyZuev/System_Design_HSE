"""Authentication service."""
import logging
from datetime import datetime, timezone
from uuid import UUID, uuid4

import bcrypt

from app.domain.exceptions import (
    InvalidCredentialsException,
    InvalidTokenException,
    RefreshTokenNotFoundException,
    RefreshTokenRevokedException,
    TokenExpiredException,
)
from app.domain.models import (
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    RefreshResponse,
    RefreshToken,
    UserSegment,
)
from app.infrastructure.jwt_handler import JWTHandler
from app.infrastructure.repositories import (
    RefreshTokenRepository,
    UserRepository,
    UserSegmentRepository,
)

logger = logging.getLogger(__name__)


class AuthService:
    """Service for authentication."""

    def __init__(
        self,
        user_repository: UserRepository,
        user_segment_repository: UserSegmentRepository,
        refresh_token_repository: RefreshTokenRepository,
        jwt_handler: JWTHandler,
    ):
        self.user_repository = user_repository
        self.user_segment_repository = user_segment_repository
        self.refresh_token_repository = refresh_token_repository
        self.jwt_handler = jwt_handler

    def _hash_password(self, password: str) -> str:
        """Hash password using bcrypt."""
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash."""
        return bcrypt.checkpw(
            password.encode("utf-8"), password_hash.encode("utf-8")
        )

    async def login(self, request: LoginRequest) -> LoginResponse:
        """Authenticate user and return tokens."""
        logger.info(f"Login attempt for email: {request.email}")

        user = await self.user_repository.get_by_email(request.email)
        if not user:
            logger.warning(f"User not found: {request.email}")
            raise InvalidCredentialsException()

        if not self._verify_password(request.password, user.password_hash):
            logger.warning(f"Invalid password for user: {user.user_id}")
            raise InvalidCredentialsException()

        if user.status.value != "ACTIVE":
            logger.warning(f"User not active: {user.user_id}")
            raise InvalidCredentialsException()

        segment_model = await self.user_segment_repository.get_by_user_id(
            user.user_id
        )
        segment = (
            segment_model.segment if segment_model else UserSegment.STANDARD
        )

        refresh_token_id = uuid4()

        # Create tokens
        access_token = self.jwt_handler.create_access_token(
            user.user_id, segment
        )
        refresh_token_str = self.jwt_handler.create_refresh_token(
            user.user_id, refresh_token_id
        )

        refresh_payload = self.jwt_handler.validate_token(refresh_token_str)
        expires_at = datetime.fromtimestamp(refresh_payload["exp"], timezone.utc)

        refresh_token = RefreshToken(
            token_id=refresh_token_id,
            user_id=user.user_id,
            expires_at=expires_at,
        )
        await self.refresh_token_repository.create(refresh_token)

        logger.info(f"User logged in successfully: {user.user_id}")

        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token_str,
            user_id=user.user_id,
        )

    async def refresh(self, request: RefreshRequest) -> RefreshResponse:
        """Refresh access token using refresh token."""
        logger.info("Refresh token request")

        try:
            payload = self.jwt_handler.validate_token(request.refresh_token)
        except (TokenExpiredException, InvalidTokenException):
            logger.warning("Invalid or expired refresh token")
            raise RefreshTokenNotFoundException()

        if payload.get("type") != "refresh":
            logger.warning("Token is not a refresh token")
            raise InvalidTokenException("Token is not a refresh token")

        user_id = UUID(payload["sub"])

        # Для простоты мы тут не используем token string,  а только token id
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            logger.warning(f"User not found for refresh token: {user_id}")
            raise RefreshTokenNotFoundException()

        if user.status.value != "ACTIVE":
            logger.warning(f"User not active: {user_id}")
            raise RefreshTokenRevokedException()

        segment_model = await self.user_segment_repository.get_by_user_id(
            user_id
        )
        segment = (
            segment_model.segment if segment_model else UserSegment.STANDARD
        )

        refresh_token_id = uuid4()

        access_token = self.jwt_handler.create_access_token(user_id, segment)
        refresh_token_str = self.jwt_handler.create_refresh_token(
            user_id, refresh_token_id
        )

        refresh_payload = self.jwt_handler.validate_token(refresh_token_str)
        expires_at = datetime.fromtimestamp(refresh_payload["exp"], timezone.utc)

        refresh_token = RefreshToken(
            token_id=refresh_token_id,
            user_id=user_id,
            expires_at=expires_at,
        )
        await self.refresh_token_repository.create(refresh_token)

        logger.info(f"Token refreshed for user: {user_id}")

        return RefreshResponse(
            access_token=access_token,
            refresh_token=refresh_token_str,
        )

