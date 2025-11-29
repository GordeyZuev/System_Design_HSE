"""Tests for AuthService."""
import pytest
from uuid import UUID
from datetime import datetime, timezone
import bcrypt

from app.domain.models import (
    LoginRequest,
    RefreshRequest,
    User,
    UserSegment,
    UserSegmentModel,
    UserStatus,
)
from app.domain.exceptions import (
    InvalidCredentialsException,
    RefreshTokenNotFoundException,
    RefreshTokenRevokedException,
)
from app.services.auth_service import AuthService
from app.infrastructure.repositories_inmemory import (
    InMemoryRefreshTokenRepository,
    InMemoryUserRepository,
    InMemoryUserSegmentRepository,
)
from app.infrastructure.jwt_handler import JWTHandler


@pytest.fixture
def jwt_handler() -> JWTHandler:
    """JWT handler fixture."""
    return JWTHandler(secret="test-secret-key")


@pytest.fixture
def auth_service(
    in_memory_user_repository: InMemoryUserRepository,
    in_memory_user_segment_repository: InMemoryUserSegmentRepository,
    in_memory_refresh_token_repository: InMemoryRefreshTokenRepository,
    jwt_handler: JWTHandler,
) -> AuthService:
    """Auth service fixture."""
    return AuthService(
        user_repository=in_memory_user_repository,
        user_segment_repository=in_memory_user_segment_repository,
        refresh_token_repository=in_memory_refresh_token_repository,
        jwt_handler=jwt_handler,
    )


@pytest.fixture
def user_with_password(mock_user_id: UUID) -> User:
    """User with hashed password."""
    password = "testpassword123"
    password_hash = bcrypt.hashpw(
        password.encode("utf-8"), bcrypt.gensalt(rounds=12)
    ).decode("utf-8")
    return User(
        user_id=mock_user_id,
        email="test@example.com",
        phone="+1234567890",
        password_hash=password_hash,
        status=UserStatus.ACTIVE,
        created_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_login_success(
    auth_service: AuthService,
    in_memory_user_repository: InMemoryUserRepository,
    in_memory_user_segment_repository: InMemoryUserSegmentRepository,
    user_with_password: User,
    mock_user_id: UUID,
) -> None:
    """Test successful login."""
    # Arrange
    await in_memory_user_repository.create(user_with_password)
    segment = UserSegmentModel(
        user_id=mock_user_id,
        segment=UserSegment.STANDARD,
        updated_at=datetime.now(timezone.utc),
    )
    await in_memory_user_segment_repository.create(segment)

    request = LoginRequest(email="test@example.com", password="testpassword123")

    # Act
    response = await auth_service.login(request)

    # Assert
    assert response.user_id == mock_user_id
    assert response.access_token is not None
    assert response.refresh_token is not None
    assert len(response.access_token) > 0
    assert len(response.refresh_token) > 0


@pytest.mark.asyncio
async def test_login_invalid_email(
    auth_service: AuthService,
    user_with_password: User,
) -> None:
    """Test login with invalid email."""
    # Arrange
    await auth_service.user_repository.create(user_with_password)
    request = LoginRequest(email="wrong@example.com", password="testpassword123")

    # Act & Assert
    with pytest.raises(InvalidCredentialsException):
        await auth_service.login(request)


@pytest.mark.asyncio
async def test_login_invalid_password(
    auth_service: AuthService,
    in_memory_user_repository: InMemoryUserRepository,
    user_with_password: User,
) -> None:
    """Test login with invalid password."""
    # Arrange
    await in_memory_user_repository.create(user_with_password)
    request = LoginRequest(email="test@example.com", password="wrongpassword")

    # Act & Assert
    with pytest.raises(InvalidCredentialsException):
        await auth_service.login(request)


@pytest.mark.asyncio
async def test_login_inactive_user(
    auth_service: AuthService,
    in_memory_user_repository: InMemoryUserRepository,
    user_with_password: User,
) -> None:
    """Test login with inactive user."""
    # Arrange
    user_with_password.status = UserStatus.INACTIVE
    await in_memory_user_repository.create(user_with_password)
    request = LoginRequest(email="test@example.com", password="testpassword123")

    # Act & Assert
    with pytest.raises(InvalidCredentialsException):
        await auth_service.login(request)


@pytest.mark.asyncio
async def test_refresh_success(
    auth_service: AuthService,
    in_memory_user_repository: InMemoryUserRepository,
    in_memory_user_segment_repository: InMemoryUserSegmentRepository,
    jwt_handler: JWTHandler,
    user_with_password: User,
    mock_user_id: UUID,
) -> None:
    """Test successful token refresh."""
    # Arrange
    await in_memory_user_repository.create(user_with_password)
    segment = UserSegmentModel(
        user_id=mock_user_id,
        segment=UserSegment.STANDARD,
        updated_at=datetime.now(timezone.utc),
    )
    await in_memory_user_segment_repository.create(segment)

    # Create a valid refresh token
    refresh_token = jwt_handler.create_refresh_token(mock_user_id)

    request = RefreshRequest(refresh_token=refresh_token)

    # Act
    response = await auth_service.refresh(request)

    # Assert
    assert response.access_token is not None
    assert response.refresh_token is not None
    assert len(response.access_token) > 0
    assert len(response.refresh_token) > 0


@pytest.mark.asyncio
async def test_refresh_invalid_token(
    auth_service: AuthService,
) -> None:
    """Test refresh with invalid token."""
    # Arrange
    request = RefreshRequest(refresh_token="invalid-token")

    # Act & Assert
    with pytest.raises(RefreshTokenNotFoundException):
        await auth_service.refresh(request)


@pytest.mark.asyncio
async def test_refresh_inactive_user(
    auth_service: AuthService,
    in_memory_user_repository: InMemoryUserRepository,
    in_memory_user_segment_repository: InMemoryUserSegmentRepository,
    jwt_handler: JWTHandler,
    user_with_password: User,
    mock_user_id: UUID,
) -> None:
    """Test refresh with inactive user."""
    # Arrange
    user_with_password.status = UserStatus.INACTIVE
    await in_memory_user_repository.create(user_with_password)
    segment = UserSegmentModel(
        user_id=mock_user_id, segment=UserSegment.STANDARD, updated_at=datetime.now(timezone.utc)
    )
    await in_memory_user_segment_repository.create(segment)

    # Create a valid refresh token
    refresh_token = jwt_handler.create_refresh_token(mock_user_id)
    request = RefreshRequest(refresh_token=refresh_token)

    # Act & Assert
    with pytest.raises(RefreshTokenRevokedException):
        await auth_service.refresh(request)

