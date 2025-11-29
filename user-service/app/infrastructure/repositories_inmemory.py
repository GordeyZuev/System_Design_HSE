"""In-memory repository implementations."""
from datetime import datetime
from typing import Dict, Optional
from uuid import UUID

from app.domain.models import (
    RefreshToken,
    User,
    UserProfile,
    UserSegment,
    UserSegmentModel,
    UserStatus,
)
from app.infrastructure.repositories import (
    RefreshTokenRepository,
    UserProfileRepository,
    UserRepository,
    UserSegmentRepository,
)


class InMemoryUserRepository(UserRepository):
    """In-memory implementation of user repository."""

    def __init__(self) -> None:
        self._users: Dict[UUID, User] = {}
        self._users_by_email: Dict[str, UUID] = {}

    async def create(self, user: User) -> User:
        """Create a new user."""
        self._users[user.user_id] = user
        self._users_by_email[user.email.lower()] = user.user_id
        return user

    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by ID."""
        return self._users.get(user_id)

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        user_id = self._users_by_email.get(email.lower())
        if user_id:
            return self._users.get(user_id)
        return None

    async def update_status(self, user_id: UUID, status: UserStatus) -> None:
        """Update user status."""
        user = self._users.get(user_id)
        if user:
            user.status = status

    def clear(self) -> None:
        """Clear all data (for testing)."""
        self._users.clear()
        self._users_by_email.clear()


class InMemoryUserProfileRepository(UserProfileRepository):
    """In-memory implementation of user profile repository."""

    def __init__(self) -> None:
        self._profiles: Dict[UUID, UserProfile] = {}

    async def create(self, profile: UserProfile) -> UserProfile:
        """Create a new user profile."""
        self._profiles[profile.user_id] = profile
        return profile

    async def get_by_user_id(self, user_id: UUID) -> Optional[UserProfile]:
        """Get profile by user ID."""
        return self._profiles.get(user_id)

    async def update(self, profile: UserProfile) -> UserProfile:
        """Update user profile."""
        self._profiles[profile.user_id] = profile
        return profile

    def clear(self) -> None:
        """Clear all data (for testing)."""
        self._profiles.clear()


class InMemoryUserSegmentRepository(UserSegmentRepository):
    """In-memory implementation of user segment repository."""

    def __init__(self) -> None:
        self._segments: Dict[UUID, UserSegmentModel] = {}

    async def create(self, segment: UserSegmentModel) -> UserSegmentModel:
        """Create a new user segment."""
        self._segments[segment.user_id] = segment
        return segment

    async def get_by_user_id(self, user_id: UUID) -> Optional[UserSegmentModel]:
        """Get segment by user ID."""
        return self._segments.get(user_id)

    async def update_segment(
        self, user_id: UUID, segment: UserSegment
    ) -> UserSegmentModel:
        """Update user segment."""
        existing = self._segments.get(user_id)
        if existing:
            existing.segment = segment
            existing.updated_at = datetime.utcnow()
            return existing
        else:
            new_segment = UserSegmentModel(user_id=user_id, segment=segment)
            self._segments[user_id] = new_segment
            return new_segment

    def clear(self) -> None:
        """Clear all data (for testing)."""
        self._segments.clear()


class InMemoryRefreshTokenRepository(RefreshTokenRepository):
    """In-memory implementation of refresh token repository."""

    def __init__(self) -> None:
        self._tokens: Dict[UUID, RefreshToken] = {}

    async def create(self, token: RefreshToken) -> RefreshToken:
        """Create a new refresh token."""
        self._tokens[token.token_id] = token
        return token

    async def get_by_token_id(self, token_id: UUID) -> Optional[RefreshToken]:
        """Get refresh token by token ID."""
        return self._tokens.get(token_id)

    async def revoke(self, token_id: UUID) -> None:
        """Revoke refresh token."""
        token = self._tokens.get(token_id)
        if token:
            token.revoked = True

    async def revoke_all_for_user(self, user_id: UUID) -> None:
        """Revoke all refresh tokens for user."""
        for token in self._tokens.values():
            if token.user_id == user_id:
                token.revoked = True

    def clear(self) -> None:
        """Clear all data (for testing)."""
        self._tokens.clear()

