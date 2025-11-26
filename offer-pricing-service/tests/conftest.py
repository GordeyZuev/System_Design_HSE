"""Pytest configuration and fixtures."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4
from datetime import datetime, timedelta

from app.domain.models import (
    Offer,
    OfferStatus,
    TariffInfo,
    UserInfo,
    UserSegment,
    ConfigData,
)
from app.infrastructure.repositories_inmemory import InMemoryOfferRepository
from app.infrastructure.clients import ConfigClient, TariffClient, UserClient
from app.services.offer_service import OfferService


@pytest.fixture
def mock_user_id() -> UUID:
    """Mock user ID."""
    return UUID("550e8400-e29b-41d4-a716-446655440000")


@pytest.fixture
def mock_station_id() -> str:
    """Mock station ID."""
    return "station-001"


@pytest.fixture
def mock_offer_id() -> UUID:
    """Mock offer ID."""
    return UUID("123e4567-e89b-12d3-a456-426614174000")


@pytest.fixture
def mock_tariff_info() -> TariffInfo:
    """Mock tariff info."""
    return TariffInfo(
        tariff_id="tariff-001",
        station_id="station-001",
        base_rate=5.0,
        segment_multiplier=1.0,
        currency="RUB",
        version="v1",
        rules={"type": "standard"},
    )


@pytest.fixture
def mock_greedy_tariff_info() -> TariffInfo:
    """Mock greedy tariff info."""
    return TariffInfo(
        tariff_id="greedy-tariff-001",
        station_id="station-001",
        base_rate=15.0,
        segment_multiplier=1.5,
        currency="RUB",
        version="greedy-v1",
        rules={"type": "greedy"},
    )


@pytest.fixture
def mock_user_info(mock_user_id: UUID) -> UserInfo:
    """Mock user info."""
    return UserInfo(
        user_id=mock_user_id,
        segment=UserSegment.STANDARD,
        status="ACTIVE",
        email="user@example.com",
    )


@pytest.fixture
def mock_config_data() -> ConfigData:
    """Mock config data."""
    return ConfigData(
        offer_ttl=300,
        max_offers_per_user=5,
        pricing_rules={"default": "standard"},
    )


@pytest.fixture
def in_memory_repository() -> InMemoryOfferRepository:
    """In-memory offer repository."""
    repo = InMemoryOfferRepository()
    yield repo
    repo.clear()


@pytest.fixture
def mock_tariff_client(mock_tariff_info: TariffInfo, mock_greedy_tariff_info: TariffInfo) -> AsyncMock:
    """Mock tariff client."""
    client = AsyncMock(spec=TariffClient)
    client.get_tariff = AsyncMock(return_value=mock_tariff_info)
    client.get_greedy_tariff = AsyncMock(return_value=mock_greedy_tariff_info)
    return client


@pytest.fixture
def mock_user_client(mock_user_info: UserInfo) -> AsyncMock:
    """Mock user client."""
    client = AsyncMock(spec=UserClient)
    client.get_user_info = AsyncMock(return_value=mock_user_info)
    client.get_user_segment = AsyncMock(return_value=mock_user_info.segment)
    return client


@pytest.fixture
def mock_config_client(mock_config_data: ConfigData) -> AsyncMock:
    """Mock config client."""
    client = AsyncMock(spec=ConfigClient)
    client.get_config = AsyncMock(return_value=mock_config_data)
    return client


@pytest.fixture
def offer_service(
    in_memory_repository: InMemoryOfferRepository,
    mock_tariff_client: AsyncMock,
    mock_user_client: AsyncMock,
    mock_config_client: AsyncMock,
) -> OfferService:
    """Offer service with mocked dependencies."""
    return OfferService(
        offer_repository=in_memory_repository,
        tariff_client=mock_tariff_client,
        user_client=mock_user_client,
        config_client=mock_config_client,
    )


@pytest.fixture
def sample_offer(mock_user_id: UUID, mock_station_id: str) -> Offer:
    """Sample offer."""
    return Offer(
        offer_id=uuid4(),
        user_id=mock_user_id,
        station_id=mock_station_id,
        tariff_snapshot={
            "tariff_id": "tariff-001",
            "base_rate": 5.0,
            "segment_multiplier": 1.0,
            "currency": "RUB",
            "segment": "STANDARD",
            "is_greedy": False,
        },
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(minutes=5),
        status=OfferStatus.ACTIVE,
        tariff_version="v1",
    )

