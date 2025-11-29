"""Tests for API endpoints."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock
from uuid import UUID

from app.main import app
from app.api.dependencies import (
    get_auth_service,
    get_user_service,
    get_jwt_handler,
)
from app.domain.models import (
    LoginResponse,
    RefreshResponse,
    UserInfo,
    UserSegment,
)
from app.domain.exceptions import (
    InvalidCredentialsException,
    UserNotFoundException,
)
from app.services.auth_service import AuthService
from app.services.user_service import UserService
from app.infrastructure.jwt_handler import JWTHandler


@pytest.fixture
def mock_auth_service() -> AsyncMock:
    """Mock auth service."""
    return AsyncMock(spec=AuthService)


@pytest.fixture
def mock_user_service() -> AsyncMock:
    """Mock user service."""
    return AsyncMock(spec=UserService)


@pytest.fixture
def mock_jwt_handler() -> AsyncMock:
    """Mock JWT handler."""
    return AsyncMock(spec=JWTHandler)


@pytest.fixture
def client(
    mock_auth_service: AsyncMock,
    mock_user_service: AsyncMock,
    mock_jwt_handler: AsyncMock,
) -> TestClient:
    """Test client with mocked dependencies."""
    app.dependency_overrides[get_auth_service] = lambda: mock_auth_service
    app.dependency_overrides[get_user_service] = lambda: mock_user_service
    app.dependency_overrides[get_jwt_handler] = lambda: mock_jwt_handler
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_root_endpoint(client: TestClient) -> None:
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "user-service"
    assert data["status"] == "running"
    assert data["storage"] == "in-memory"


def test_health_endpoint(client: TestClient) -> None:
    """Test health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_metrics_endpoint(client: TestClient) -> None:
    """Test metrics endpoint."""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "python_info" in response.text


@pytest.mark.asyncio
async def test_login_success(
    client: TestClient,
    mock_auth_service: AsyncMock,
    mock_user_id: UUID,
) -> None:
    """Test login endpoint success."""
    # Arrange
    mock_response = LoginResponse(
        access_token="test-access-token",
        refresh_token="test-refresh-token",
        user_id=mock_user_id,
    )
    mock_auth_service.login = AsyncMock(return_value=mock_response)

    # Act
    response = client.post(
        "/auth/login",
        json={"email": "test@example.com", "password": "testpassword123"},
    )

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["access_token"] == "test-access-token"
    assert data["refresh_token"] == "test-refresh-token"
    assert data["user_id"] == str(mock_user_id)


@pytest.mark.asyncio
async def test_login_invalid_credentials(
    client: TestClient,
    mock_auth_service: AsyncMock,
) -> None:
    """Test login with invalid credentials."""
    # Arrange
    mock_auth_service.login = AsyncMock(
        side_effect=InvalidCredentialsException()
    )

    # Act
    response = client.post(
        "/auth/login",
        json={"email": "test@example.com", "password": "wrongpassword"},
    )

    # Assert
    assert response.status_code == 401
    data = response.json()
    assert data["detail"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_refresh_success(
    client: TestClient,
    mock_auth_service: AsyncMock,
) -> None:
    """Test refresh endpoint success."""
    # Arrange
    mock_response = RefreshResponse(
        access_token="new-access-token",
        refresh_token="new-refresh-token",
    )
    mock_auth_service.refresh = AsyncMock(return_value=mock_response)

    # Act
    response = client.post(
        "/auth/refresh",
        json={"refresh_token": "old-refresh-token"},
    )

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["access_token"] == "new-access-token"
    assert data["refresh_token"] == "new-refresh-token"


@pytest.mark.asyncio
async def test_get_user_success(
    client: TestClient,
    mock_user_service: AsyncMock,
    mock_user_id: UUID,
) -> None:
    """Test get user endpoint success."""
    # Arrange
    mock_user_info = UserInfo(
        user_id=mock_user_id,
        email="test@example.com",
        segment=UserSegment.STANDARD,
        status="ACTIVE",
        phone="+1234567890",
    )
    mock_user_service.get_user_info = AsyncMock(return_value=mock_user_info)

    # Act
    response = client.get(f"/api/v1/users/{mock_user_id}")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == str(mock_user_id)
    assert data["email"] == "test@example.com"
    assert data["segment"] == "STANDARD"
    assert data["status"] == "ACTIVE"


@pytest.mark.asyncio
async def test_get_all_users_success(
    client: TestClient,
    mock_user_service: AsyncMock,
    mock_user_id: UUID,
) -> None:
    """Test get all users endpoint success."""
    # Arrange
    from app.domain.models import UserInfo, UserSegment

    mock_users_info = [
        UserInfo(
            user_id=mock_user_id,
            email="test1@example.com",
            segment=UserSegment.STANDARD,
            status="ACTIVE",
            phone="+1234567890",
        ),
        UserInfo(
            user_id=UUID("550e8400-e29b-41d4-a716-446655440001"),
            email="test2@example.com",
            segment=UserSegment.PREMIUM,
            status="ACTIVE",
            phone="+1234567891",
        ),
    ]
    mock_user_service.get_all_users = AsyncMock(return_value=mock_users_info)

    # Act
    response = client.get("/api/v1/users")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "users" in data
    assert "total" in data
    assert data["total"] == 2
    assert len(data["users"]) == 2
    assert data["users"][0]["email"] == "test1@example.com"
    assert data["users"][1]["email"] == "test2@example.com"


@pytest.mark.asyncio
async def test_get_all_users_empty(
    client: TestClient,
    mock_user_service: AsyncMock,
) -> None:
    """Test get all users with empty list."""
    # Arrange
    mock_user_service.get_all_users = AsyncMock(return_value=[])

    # Act
    response = client.get("/api/v1/users")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "users" in data
    assert "total" in data
    assert data["total"] == 0
    assert data["users"] == []


@pytest.mark.asyncio
async def test_get_user_not_found(
    client: TestClient,
    mock_user_service: AsyncMock,
    mock_user_id: UUID,
) -> None:
    """Test get user not found."""
    # Arrange
    mock_user_service.get_user_info = AsyncMock(
        side_effect=UserNotFoundException(user_id=str(mock_user_id))
    )

    # Act
    response = client.get(f"/api/v1/users/{mock_user_id}")

    # Assert
    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["code"] == "USER_NOT_FOUND"


@pytest.mark.asyncio
async def test_validate_jwt_success(
    client: TestClient,
    mock_jwt_handler: JWTHandler,
    mock_user_id: UUID,
) -> None:
    """Test JWT validation endpoint success."""
    # Arrange
    jwt_handler = JWTHandler(secret="test-secret")
    token = jwt_handler.create_access_token(
        mock_user_id, UserSegment.STANDARD
    )

    # Override with real handler for this test
    app.dependency_overrides[get_jwt_handler] = lambda: jwt_handler

    # Act
    response = client.post(
        "/api/v1/jwt/validate",
        json={"token": token},
    )

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
    assert data["user_id"] == str(mock_user_id)
    assert data["segment"] == "STANDARD"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_validate_jwt_invalid(
    client: TestClient,
    mock_jwt_handler: JWTHandler,
) -> None:
    """Test JWT validation with invalid token."""
    # Arrange
    jwt_handler = JWTHandler(secret="test-secret")
    app.dependency_overrides[get_jwt_handler] = lambda: jwt_handler

    # Act
    response = client.post(
        "/api/v1/jwt/validate",
        json={"token": "invalid-token"},
    )

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_refresh_invalid_token(
    client: TestClient,
    mock_auth_service: AsyncMock,
) -> None:
    """Test refresh with invalid token."""
    # Arrange
    from app.domain.exceptions import RefreshTokenNotFoundException
    mock_auth_service.refresh = AsyncMock(
        side_effect=RefreshTokenNotFoundException()
    )

    # Act
    response = client.post(
        "/auth/refresh",
        json={"refresh_token": "invalid-token"},
    )

    # Assert
    assert response.status_code == 401
    data = response.json()
    assert data["detail"]["code"] == "REFRESH_TOKEN_NOT_FOUND"


@pytest.mark.asyncio
async def test_refresh_revoked_token(
    client: TestClient,
    mock_auth_service: AsyncMock,
) -> None:
    """Test refresh with revoked token."""
    # Arrange
    from app.domain.exceptions import RefreshTokenRevokedException
    mock_auth_service.refresh = AsyncMock(
        side_effect=RefreshTokenRevokedException()
    )

    # Act
    response = client.post(
        "/auth/refresh",
        json={"refresh_token": "revoked-token"},
    )

    # Assert
    assert response.status_code == 401
    data = response.json()
    assert data["detail"]["code"] == "REFRESH_TOKEN_REVOKED"


@pytest.mark.asyncio
async def test_login_missing_fields(client: TestClient) -> None:
    """Test login with missing fields."""
    # Act
    response = client.post(
        "/auth/login",
        json={},  # Empty JSON
    )

    # Assert
    assert response.status_code == 422  # Validation error


