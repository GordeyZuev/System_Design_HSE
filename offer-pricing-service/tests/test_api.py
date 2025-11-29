"""Tests for API endpoints."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock
from uuid import UUID

from app.main import app
from app.api.dependencies import get_offer_service
from app.domain.models import CreateOfferResponse, GetOfferResponse, OfferStatus
from app.domain.exceptions import OfferNotFoundException
from app.services.offer_service import OfferService
from datetime import datetime, timedelta


@pytest.fixture
def mock_offer_service() -> AsyncMock:
    """Mock offer service."""
    return AsyncMock(spec=OfferService)


@pytest.fixture
def client(mock_offer_service: AsyncMock) -> TestClient:
    """Test client with mocked dependencies."""
    app.dependency_overrides[get_offer_service] = lambda: mock_offer_service
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def mock_create_offer_response(mock_offer_id: UUID) -> CreateOfferResponse:
    """Mock create offer response."""
    return CreateOfferResponse(
        offer_id=mock_offer_id,
        expires_at=datetime.utcnow() + timedelta(minutes=5),
        tariff_details={
            "tariff_id": "tariff-001",
            "base_rate": 5.0,
            "segment_multiplier": 1.0,
            "currency": "RUB",
        },
        estimated_rate_per_minute=5.0,
        currency="RUB",
    )


@pytest.fixture
def mock_get_offer_response(mock_offer_id: UUID, mock_user_id: UUID) -> GetOfferResponse:
    """Mock get offer response."""
    return GetOfferResponse(
        offer_id=mock_offer_id,
        user_id=mock_user_id,
        station_id="station-001",
        status=OfferStatus.ACTIVE,
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(minutes=5),
        tariff_snapshot={"tariff_id": "tariff-001"},
        is_valid=True,
    )


def test_root_endpoint(client: TestClient) -> None:
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "offer-pricing-service"
    assert data["status"] == "running"
    assert data["storage"] == "PostgreSQL"


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


def test_create_offer_success(
    client: TestClient,
    mock_offer_service: AsyncMock,
    mock_user_id: UUID,
    mock_station_id: str,
    mock_create_offer_response: CreateOfferResponse,
) -> None:
    """Test create offer endpoint."""
    # Arrange
    mock_offer_service.create_offer = AsyncMock(return_value=mock_create_offer_response)

    # Act
    response = client.post(
        "/internal/offers",
        json={
            "user_id": str(mock_user_id),
            "station_id": mock_station_id,
            "user_segment": "STANDARD",
        },
    )

    # Assert
    assert response.status_code == 201
    data = response.json()
    assert "offer_id" in data
    assert "expires_at" in data
    assert data["estimated_rate_per_minute"] == 5.0


def test_get_offer_success(
    client: TestClient,
    mock_offer_service: AsyncMock,
    mock_offer_id: UUID,
    mock_get_offer_response: GetOfferResponse,
) -> None:
    """Test get offer endpoint."""
    # Arrange
    mock_offer_service.get_offer = AsyncMock(return_value=mock_get_offer_response)

    # Act
    response = client.get(f"/internal/offers/{mock_offer_id}")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["offer_id"] == str(mock_offer_id)
    assert data["status"] == "ACTIVE"
    assert data["is_valid"] is True


def test_get_offer_not_found(
    client: TestClient,
    mock_offer_service: AsyncMock,
    mock_offer_id: UUID,
) -> None:
    """Test get offer not found."""
    # Arrange
    mock_offer_service.get_offer = AsyncMock(
        side_effect=OfferNotFoundException(str(mock_offer_id))
    )

    # Act
    response = client.get(f"/internal/offers/{mock_offer_id}")

    # Assert
    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["code"] == "OFFER_NOT_FOUND"


def test_validate_offer_success(
    client: TestClient,
    mock_offer_service: AsyncMock,
    mock_offer_id: UUID,
    mock_user_id: UUID,
    sample_offer,
) -> None:
    """Test validate offer endpoint."""
    # Arrange
    mock_offer_service.validate_and_use_offer = AsyncMock(return_value=sample_offer)

    # Act
    response = client.post(
        f"/internal/offers/{mock_offer_id}/validate",
        params={"user_id": str(mock_user_id)},
    )

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "VALIDATED"
    assert "tariff_snapshot" in data

