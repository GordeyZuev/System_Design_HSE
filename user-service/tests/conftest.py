"""Pytest configuration and fixtures."""
import pytest
from uuid import UUID
from datetime import datetime, timezone

from app.domain.models import (
    User,
    UserProfile,
    UserSegment,
    UserSegmentModel,
    UserStatus,
)
from app.infrastructure.repositories_inmemory import (
    InMemoryRefreshTokenRepository,
    InMemoryUserProfileRepository,
    InMemoryUserRepository,
    InMemoryUserSegmentRepository,
)


@pytest.fixture
def mock_user_id() -> UUID:
    """Mock user ID."""
    return UUID("550e8400-e29b-41d4-a716-446655440000")


@pytest.fixture
def sample_user(mock_user_id: UUID) -> User:
    """Sample user."""
    return User(
        user_id=mock_user_id,
        email="test@example.com",
        phone="+1234567890",
        password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqJqZqZqZq",
        status=UserStatus.ACTIVE,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_user_profile(mock_user_id: UUID) -> UserProfile:
    """Sample user profile."""
    return UserProfile(
        user_id=mock_user_id,
        name="Test User",
        extra_metadata_json={},
    )


@pytest.fixture
def sample_user_segment(mock_user_id: UUID) -> UserSegmentModel:
    """Sample user segment."""
    return UserSegmentModel(
        user_id=mock_user_id,
        segment=UserSegment.STANDARD,
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def in_memory_user_repository() -> InMemoryUserRepository:
    """In-memory user repository."""
    repo = InMemoryUserRepository()
    yield repo
    repo.clear()


@pytest.fixture
def in_memory_user_profile_repository() -> InMemoryUserProfileRepository:
    """In-memory user profile repository."""
    repo = InMemoryUserProfileRepository()
    yield repo
    repo.clear()


@pytest.fixture
def in_memory_user_segment_repository() -> InMemoryUserSegmentRepository:
    """In-memory user segment repository."""
    repo = InMemoryUserSegmentRepository()
    yield repo
    repo.clear()


@pytest.fixture
def in_memory_refresh_token_repository() -> InMemoryRefreshTokenRepository:
    """In-memory refresh token repository."""
    repo = InMemoryRefreshTokenRepository()
    yield repo
    repo.clear()

