"""JWT handler for token creation and validation."""
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List
from uuid import UUID, uuid4

import jwt

from app.config import settings
from app.domain.exceptions import InvalidTokenException, TokenExpiredException
from app.domain.models import UserSegment

logger = logging.getLogger(__name__)


class JWTHandler:
    """JWT handler for creating and validating tokens."""

    def __init__(self, secret: str = settings.jwt_secret, algorithm: str = "HS256"):
        self.secret = secret
        self.algorithm = algorithm

    def create_access_token(
        self,
        user_id: UUID,
        segment: UserSegment,
        roles: List[str] = None,
        expires_in_minutes: int = 15,
    ) -> str:
        """Create access token."""
        if roles is None:
            roles = ["user"]

        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(user_id),
            "segment": segment.value,
            "roles": roles,
            "iat": now,
            "exp": now + timedelta(minutes=expires_in_minutes),
            "type": "access",
        }

        token = jwt.encode(payload, self.secret, algorithm=self.algorithm)
        return token

    def create_refresh_token(
        self, user_id: UUID, token_id: UUID = None, expires_in_days: int = 7
    ) -> str:
        """Create refresh token."""
        now = datetime.now(timezone.utc)
        if token_id is None:
            token_id = uuid4()
        payload = {
            "sub": str(user_id),
            "jti": str(token_id),
            "iat": now,
            "exp": now + timedelta(days=expires_in_days),
            "type": "refresh",
        }

        token = jwt.encode(payload, self.secret, algorithm=self.algorithm)
        return token

    def validate_token(self, token: str) -> Dict:
        """Validate and decode token."""
        try:
            payload = jwt.decode(token, self.secret, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            raise TokenExpiredException()
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            raise InvalidTokenException(f"Invalid token: {e}")

    def validate_access_token(self, token: str) -> Dict:
        """Validate access token specifically."""
        payload = self.validate_token(token)
        if payload.get("type") != "access":
            raise InvalidTokenException("Token is not an access token")
        return payload

    def get_user_id_from_token(self, token: str) -> UUID:
        """Extract user ID from token."""
        payload = self.validate_access_token(token)
        return UUID(payload["sub"])

    def get_segment_from_token(self, token: str) -> UserSegment:
        """Extract segment from token."""
        payload = self.validate_access_token(token)
        return UserSegment(payload["segment"])

    def get_roles_from_token(self, token: str) -> List[str]:
        """Extract roles from token."""
        payload = self.validate_access_token(token)
        return payload.get("roles", [])

