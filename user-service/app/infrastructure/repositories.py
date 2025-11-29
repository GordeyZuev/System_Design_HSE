"""Abstract repository interfaces."""
from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from app.domain.models import (
    RefreshToken,
    User,
    UserProfile,
    UserSegment,
    UserSegmentModel,
    UserStatus,
)


class UserRepository(ABC):
    """Abstract user repository interface."""

    @abstractmethod
    async def create(self, user: User) -> User:
        """Create a new user."""
        pass

    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by ID."""
        pass

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        pass

    @abstractmethod
    async def update_status(self, user_id: UUID, status: UserStatus) -> None:
        """Update user status."""
        pass


class UserProfileRepository(ABC):
    """Abstract user profile repository interface."""

    @abstractmethod
    async def create(self, profile: UserProfile) -> UserProfile:
        """Create a new user profile."""
        pass

    @abstractmethod
    async def get_by_user_id(self, user_id: UUID) -> Optional[UserProfile]:
        """Get profile by user ID."""
        pass

    @abstractmethod
    async def update(self, profile: UserProfile) -> UserProfile:
        """Update user profile."""
        pass


class UserSegmentRepository(ABC):
    """Abstract user segment repository interface."""

    @abstractmethod
    async def create(self, segment: UserSegmentModel) -> UserSegmentModel:
        """Create a new user segment."""
        pass

    @abstractmethod
    async def get_by_user_id(self, user_id: UUID) -> Optional[UserSegmentModel]:
        """Get segment by user ID."""
        pass

    @abstractmethod
    async def update_segment(
        self, user_id: UUID, segment: UserSegment
    ) -> UserSegmentModel:
        """Update user segment."""
        pass


class RefreshTokenRepository(ABC):
    """Abstract refresh token repository interface."""

    @abstractmethod
    async def create(self, token: RefreshToken) -> RefreshToken:
        """Create a new refresh token."""
        pass

    @abstractmethod
    async def get_by_token_id(self, token_id: UUID) -> Optional[RefreshToken]:
        """Get refresh token by token ID."""
        pass

    @abstractmethod
    async def revoke(self, token_id: UUID) -> None:
        """Revoke refresh token."""
        pass

    @abstractmethod
    async def revoke_all_for_user(self, user_id: UUID) -> None:
        """Revoke all refresh tokens for user."""
        pass

