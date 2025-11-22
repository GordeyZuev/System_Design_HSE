"""Pytest configuration and fixtures for RentalService."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4
from datetime import datetime, timezone, timedelta

from app.services.rental_service import RentalService
from app.infrastructure.repository import RentalRepository
from app.infrastructure.clients.offer_client import OfferClient
from app.infrastructure.clients.stations_adapter_client import StationsAdapter
from app.domain.exception import (
    OfferNotActiveException,
    ExpireAtNotFoundException,
    UserAlreadyRentException,
    OfferNotBelongUserException,
    OfferExpiredException,
    RentalNotFoundException,
    UserIdsMismatchException,
    RentalAlreadyFinishedException,
)

@pytest.fixture
def mock_user_id() -> UUID:
    return UUID("550e8400-e29b-41d4-a716-446655440000")

@pytest.fixture
def mock_offer_id() -> UUID:
    return UUID("123e4567-e89b-12d3-a456-426614174000")

@pytest.fixture
def mock_rental_repo() -> AsyncMock:
    repo = AsyncMock(spec=RentalRepository)

    # Default return values
    repo.get_by_user_id.return_value = None
    repo.get_by_offer_id_active.return_value = None
    repo.create_rental.return_value = MagicMock(
        rental_id=uuid4(),
        status="ACTIVE",
        started_at=datetime.now(timezone.utc),
    )
    repo.get.return_value = MagicMock(
        rental_id=uuid4(),
        user_id=uuid4(),
        status="ACTIVE",
        started_at=datetime.now(timezone.utc),
    )
    repo.finish_rental.return_value = MagicMock(
        rental_id=uuid4(),
        finished_at=datetime.now(timezone.utc),
        final_cost=15.0,
    )
    return repo

@pytest.fixture
def mock_offer_client(mock_user_id: UUID) -> AsyncMock:
    client = AsyncMock(spec=OfferClient)
    client.get_offer.return_value = {
        "status": "ACTIVE",
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
        "user_id": str(mock_user_id),
        "tariff_snapshot": {"initial_fee": 10, "per_minute": 1},
        "tariff_version": 1,
        "station_id": "ST1",
    }
    return client


@pytest.fixture
def mock_stations_adapter() -> AsyncMock:
    adapter = AsyncMock(spec=StationsAdapter)
    adapter.reserve_or_issue.return_value = {"success": True}
    adapter.return_powerbank.return_value = {"success": True}
    return adapter


@pytest.fixture
def rental_service(
    mock_rental_repo: AsyncMock,
    mock_offer_client: AsyncMock,
    mock_stations_adapter: AsyncMock,
) -> RentalService:
    """Real RentalService with mocked dependencies."""
    service = RentalService(
        session=MagicMock(),
        offer_client=mock_offer_client,
        stations_adapter=mock_stations_adapter,
    )
    service.repo = mock_rental_repo
    return service


@pytest.fixture
def sample_rental(mock_user_id: UUID) -> MagicMock:
    rental = MagicMock()
    rental.rental_id = uuid4()
    rental.user_id = mock_user_id
    rental.status = "ACTIVE"
    rental.started_at = datetime.now(timezone.utc)
    rental.finished_at = None
    rental.tariff_snapshot = {"initial_fee": 10, "per_minute": 1}
    return rental
