"""Tests for repositories."""
import pytest
from uuid import UUID
from datetime import datetime, timedelta

from app.domain.models import Offer, OfferStatus
from app.infrastructure.repositories_inmemory import InMemoryOfferRepository


@pytest.mark.asyncio
async def test_create_offer(
    in_memory_repository: InMemoryOfferRepository,
    sample_offer: Offer,
) -> None:
    """Test creating an offer."""
    # Act
    created = await in_memory_repository.create(sample_offer)

    # Assert
    assert created.offer_id == sample_offer.offer_id
    assert len(in_memory_repository._audit_events) == 1
    assert in_memory_repository._audit_events[0]["event_type"] == "CREATED"


@pytest.mark.asyncio
async def test_get_offer_by_id(
    in_memory_repository: InMemoryOfferRepository,
    sample_offer: Offer,
) -> None:
    """Test getting offer by ID."""
    # Arrange
    await in_memory_repository.create(sample_offer)

    # Act
    retrieved = await in_memory_repository.get_by_id(sample_offer.offer_id)

    # Assert
    assert retrieved is not None
    assert retrieved.offer_id == sample_offer.offer_id
    assert retrieved.user_id == sample_offer.user_id


@pytest.mark.asyncio
async def test_get_offer_by_id_not_found(
    in_memory_repository: InMemoryOfferRepository,
    mock_offer_id: UUID,
) -> None:
    """Test getting non-existent offer."""
    # Act
    retrieved = await in_memory_repository.get_by_id(mock_offer_id)

    # Assert
    assert retrieved is None


@pytest.mark.asyncio
async def test_update_offer_status(
    in_memory_repository: InMemoryOfferRepository,
    sample_offer: Offer,
) -> None:
    """Test updating offer status."""
    # Arrange
    await in_memory_repository.create(sample_offer)

    # Act
    await in_memory_repository.update_status(sample_offer.offer_id, OfferStatus.USED)

    # Assert
    retrieved = await in_memory_repository.get_by_id(sample_offer.offer_id)
    assert retrieved is not None
    assert retrieved.status == OfferStatus.USED
    
    # Check audit
    status_events = [
        e for e in in_memory_repository._audit_events
        if e["event_type"] == "STATUS_CHANGED"
    ]
    assert len(status_events) == 1
    assert status_events[0]["payload"]["new_status"] == "USED"


@pytest.mark.asyncio
async def test_get_active_by_user(
    in_memory_repository: InMemoryOfferRepository,
    mock_user_id: UUID,
    mock_station_id: str,
) -> None:
    """Test getting active offers by user."""
    # Arrange
    # Create active offer
    active_offer = Offer(
        user_id=mock_user_id,
        station_id=mock_station_id,
        tariff_snapshot={"test": "data"},
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(minutes=5),
        status=OfferStatus.ACTIVE,
    )
    await in_memory_repository.create(active_offer)

    # Create expired offer
    expired_offer = Offer(
        user_id=mock_user_id,
        station_id=mock_station_id,
        tariff_snapshot={"test": "data"},
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() - timedelta(minutes=1),
        status=OfferStatus.ACTIVE,
    )
    await in_memory_repository.create(expired_offer)

    # Create used offer
    used_offer = Offer(
        user_id=mock_user_id,
        station_id=mock_station_id,
        tariff_snapshot={"test": "data"},
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(minutes=5),
        status=OfferStatus.USED,
    )
    await in_memory_repository.create(used_offer)

    # Act
    active_offers = await in_memory_repository.get_active_by_user(mock_user_id)

    # Assert
    assert len(active_offers) == 1
    assert active_offers[0].offer_id == active_offer.offer_id


@pytest.mark.asyncio
async def test_clear_repository(
    in_memory_repository: InMemoryOfferRepository,
    sample_offer: Offer,
) -> None:
    """Test clearing repository."""
    # Arrange
    await in_memory_repository.create(sample_offer)
    assert len(in_memory_repository._offers) == 1

    # Act
    in_memory_repository.clear()

    # Assert
    assert len(in_memory_repository._offers) == 0
    assert len(in_memory_repository._audit_events) == 0

