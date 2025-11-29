"""Tests for UserService."""
import pytest
from uuid import UUID

from app.domain.models import (
    User,
    UserSegment,
    UserSegmentModel,
)
from app.domain.exceptions import UserNotFoundException
from app.services.user_service import UserService
from app.infrastructure.repositories_inmemory import (
    InMemoryUserProfileRepository,
    InMemoryUserRepository,
    InMemoryUserSegmentRepository,
)


@pytest.fixture
def user_service(
    in_memory_user_repository: InMemoryUserRepository,
    in_memory_user_profile_repository: InMemoryUserProfileRepository,
    in_memory_user_segment_repository: InMemoryUserSegmentRepository,
) -> UserService:
    """User service fixture."""
    return UserService(
        user_repository=in_memory_user_repository,
        user_profile_repository=in_memory_user_profile_repository,
        user_segment_repository=in_memory_user_segment_repository,
        cache_ttl=60,
    )


@pytest.mark.asyncio
async def test_get_user_info_success(
    user_service: UserService,
    in_memory_user_repository: InMemoryUserRepository,
    in_memory_user_segment_repository: InMemoryUserSegmentRepository,
    sample_user: User,
    sample_user_segment: UserSegmentModel,
    mock_user_id: UUID,
) -> None:
    """Test successful user info retrieval."""
    # Arrange
    await in_memory_user_repository.create(sample_user)
    await in_memory_user_segment_repository.create(sample_user_segment)

    # Act
    user_info = await user_service.get_user_info(mock_user_id)

    # Assert
    assert user_info.user_id == mock_user_id
    assert user_info.email == "test@example.com"
    assert user_info.segment == UserSegment.STANDARD
    assert user_info.status == "ACTIVE"
    assert user_info.phone == "+1234567890"


@pytest.mark.asyncio
async def test_get_user_info_not_found(
    user_service: UserService,
    mock_user_id: UUID,
) -> None:
    """Test user info retrieval for non-existent user."""
    # Act & Assert
    with pytest.raises(UserNotFoundException):
        await user_service.get_user_info(mock_user_id)


@pytest.mark.asyncio
async def test_get_user_info_without_segment(
    user_service: UserService,
    in_memory_user_repository: InMemoryUserRepository,
    sample_user: User,
    mock_user_id: UUID,
) -> None:
    """Test user info retrieval when segment doesn't exist (should default to STANDARD)."""
    # Arrange
    await in_memory_user_repository.create(sample_user)
    # Don't create segment

    # Act
    user_info = await user_service.get_user_info(mock_user_id)

    # Assert
    assert user_info.user_id == mock_user_id
    assert user_info.segment == UserSegment.STANDARD  # Default segment


@pytest.mark.asyncio
async def test_get_user_info_caching(
    user_service: UserService,
    in_memory_user_repository: InMemoryUserRepository,
    in_memory_user_segment_repository: InMemoryUserSegmentRepository,
    sample_user: User,
    sample_user_segment: UserSegmentModel,
    mock_user_id: UUID,
) -> None:
    """Test that user info is cached."""
    # Arrange
    await in_memory_user_repository.create(sample_user)
    await in_memory_user_segment_repository.create(sample_user_segment)

    # Act - first call
    user_info1 = await user_service.get_user_info(mock_user_id)

    # Delete user from repository to verify cache is used
    user_service.user_repository._users.clear()

    # Act - second call should use cache
    user_info2 = await user_service.get_user_info(mock_user_id)

    # Assert
    assert user_info1.user_id == user_info2.user_id
    assert user_info1.email == user_info2.email


@pytest.mark.asyncio
async def test_get_user_info_cache_expiration(
    user_service: UserService,
    in_memory_user_repository: InMemoryUserRepository,
    in_memory_user_segment_repository: InMemoryUserSegmentRepository,
    sample_user: User,
    sample_user_segment: UserSegmentModel,
    mock_user_id: UUID,
) -> None:
    """Test that cache expires after TTL."""
    # Arrange - use very short TTL
    user_service.cache_ttl = 0.1  # 100ms
    await in_memory_user_repository.create(sample_user)
    await in_memory_user_segment_repository.create(sample_user_segment)

    # Act - first call to populate cache
    await user_service.get_user_info(mock_user_id)

    # Wait for cache to expire
    import time
    time.sleep(0.2)

    # Delete user from repository to verify cache is expired
    user_service.user_repository._users.clear()

    # Act - second call should fail because cache expired and user is deleted
    with pytest.raises(UserNotFoundException):
        await user_service.get_user_info(mock_user_id)

