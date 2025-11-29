"""User service."""
import logging
import time
from typing import Optional
from uuid import UUID

from app.domain.exceptions import UserNotFoundException
from app.domain.models import UserInfo, UserSegment
from app.infrastructure.repositories import (
    UserProfileRepository,
    UserRepository,
    UserSegmentRepository,
)

logger = logging.getLogger(__name__)


class UserService:
    """Service for user operations."""

    def __init__(
        self,
        user_repository: UserRepository,
        user_profile_repository: UserProfileRepository,
        user_segment_repository: UserSegmentRepository,
        cache_ttl: int = 60,
    ):
        self.user_repository = user_repository
        self.user_profile_repository = user_profile_repository
        self.user_segment_repository = user_segment_repository
        self.cache_ttl = cache_ttl
        self._cache: dict = {}
        self._cache_timestamps: dict = {}

    def _get_from_cache(self, user_id: UUID) -> Optional[UserInfo]:
        """Get user info from cache if valid."""
        if user_id not in self._cache:
            return None

        current_time = time.time()
        if current_time - self._cache_timestamps[user_id] > self.cache_ttl:
            del self._cache[user_id]
            del self._cache_timestamps[user_id]
            return None

        return self._cache[user_id]

    def _set_cache(self, user_id: UUID, user_info: UserInfo) -> None:
        """Store user info in cache."""
        self._cache[user_id] = user_info
        self._cache_timestamps[user_id] = time.time()

    async def get_user_info(self, user_id: UUID) -> UserInfo:
        """Get user information with caching."""
        cached = self._get_from_cache(user_id)
        if cached:
            logger.debug(f"Returning cached user info for {user_id}")
            return cached

        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise UserNotFoundException(user_id=str(user_id))

        segment_model = await self.user_segment_repository.get_by_user_id(
            user_id
        )
        segment = (
            segment_model.segment if segment_model else UserSegment.STANDARD
        )

        user_info = UserInfo(
            user_id=user.user_id,
            email=user.email,
            segment=segment,
            status=user.status.value,
            phone=user.phone,
        )

        self._set_cache(user_id, user_info)

        logger.info(f"Retrieved user info for {user_id}")
        return user_info

    async def get_all_users(self) -> list[UserInfo]:
        """Get all users information."""
        users = await self.user_repository.get_all()
        result = []

        for user in users:
            segment_model = await self.user_segment_repository.get_by_user_id(
                user.user_id
            )
            segment = (
                segment_model.segment if segment_model else UserSegment.STANDARD
            )

            user_info = UserInfo(
                user_id=user.user_id,
                email=user.email,
                segment=segment,
                status=user.status.value,
                phone=user.phone,
            )
            result.append(user_info)

        logger.info(f"Retrieved {len(result)} users")
        return result

