"""User Service client."""
import logging
from uuid import UUID

from app.config import settings
from app.domain.exceptions import UserServiceUnavailableException
from app.domain.models import UserInfo, UserSegment
from app.infrastructure.clients.base import BaseHTTPClient

logger = logging.getLogger(__name__)


class UserClient:
    """Client for User Service (Auth & Profile)."""

    def __init__(
        self,
        base_url: str = settings.user_service_url,
        timeout: float = settings.user_service_timeout,
    ):
        self.http_client = BaseHTTPClient(base_url, timeout)

    async def close(self) -> None:
        """Close the client."""
        await self.http_client.close()

    async def get_user_info(self, user_id: UUID) -> UserInfo:
        """Get user information including segment and status."""
        try:
            logger.info(f"Fetching user info for {user_id}")
            response = await self.http_client.get(f"/api/v1/users/{user_id}")

            if not response or "user_id" not in response:
                raise UserServiceUnavailableException()

            return UserInfo(
                user_id=UUID(response["user_id"]),
                segment=UserSegment(response.get("segment", "STANDARD")),
                status=response.get("status", "ACTIVE"),
                email=response.get("email"),
            )
        except Exception as e:
            logger.error(f"Failed to fetch user info for {user_id}: {e}")
            raise UserServiceUnavailableException()

    async def get_user_segment(self, user_id: UUID) -> UserSegment:
        """Get user segment only."""
        user_info = await self.get_user_info(user_id)
        return user_info.segment

