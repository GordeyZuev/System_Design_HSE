"""Tests for PostgreSQL repository."""
import pytest
from uuid import UUID, uuid4
from datetime import datetime, timedelta

from app.domain.models import Offer, OfferStatus
from app.infrastructure.repositories_postgres import PostgresOfferRepository
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_create_offer(
    repository: PostgresOfferRepository,
    sample_offer: Offer,
    async_session: AsyncSession,
) -> None:
    """Test creating an offer."""
    # Act
    created = await repository.create(sample_offer)
    await async_session.commit()

    # Assert
    assert created.offer_id == sample_offer.offer_id
    assert created.user_id == sample_offer.user_id
    assert created.station_id == sample_offer.station_id


@pytest.mark.asyncio
async def test_get_offer_by_id(
    repository: PostgresOfferRepository,
    sample_offer: Offer,
    async_session: AsyncSession,
) -> None:
    """Test getting offer by ID."""
    # Arrange
    await repository.create(sample_offer)
    await async_session.commit()

    # Act
    retrieved = await repository.get_by_id(sample_offer.offer_id)

    # Assert
    assert retrieved is not None
    assert retrieved.offer_id == sample_offer.offer_id
    assert retrieved.user_id == sample_offer.user_id


@pytest.mark.asyncio
async def test_get_offer_by_id_not_found(
    repository: PostgresOfferRepository,
    mock_offer_id: UUID,
) -> None:
    """Test getting non-existent offer."""
    # Act
    retrieved = await repository.get_by_id(mock_offer_id)

    # Assert
    assert retrieved is None


@pytest.mark.asyncio
async def test_update_offer_status(
    repository: PostgresOfferRepository,
    sample_offer: Offer,
    async_session: AsyncSession,
) -> None:
    """Test updating offer status."""
    # Arrange
    await repository.create(sample_offer)
    await async_session.commit()

    # Act
    await repository.update_status(sample_offer.offer_id, OfferStatus.USED)
    await async_session.commit()

    # Assert
    retrieved = await repository.get_by_id(sample_offer.offer_id)
    assert retrieved is not None
    assert retrieved.status == OfferStatus.USED


@pytest.mark.asyncio
async def test_get_active_by_user(
    repository: PostgresOfferRepository,
    mock_user_id: UUID,
    mock_station_id: str,
    async_session: AsyncSession,
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
    await repository.create(active_offer)

    # Create expired offer (should not be returned)
    expired_offer = Offer(
        user_id=mock_user_id,
        station_id=mock_station_id,
        tariff_snapshot={"test": "data"},
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() - timedelta(minutes=1),
        status=OfferStatus.ACTIVE,
    )
    await repository.create(expired_offer)

    # Create used offer (should not be returned)
    used_offer = Offer(
        user_id=mock_user_id,
        station_id=mock_station_id,
        tariff_snapshot={"test": "data"},
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(minutes=5),
        status=OfferStatus.USED,
    )
    await repository.create(used_offer)

    await async_session.commit()

    # Act
    active_offers = await repository.get_active_by_user(mock_user_id)

    # Assert
    assert len(active_offers) == 1
    assert active_offers[0].offer_id == active_offer.offer_id


@pytest.mark.asyncio
async def test_log_audit_event(
    repository: PostgresOfferRepository,
    sample_offer: Offer,
    async_session: AsyncSession,
) -> None:
    """Test logging audit event."""
    # Arrange
    await repository.create(sample_offer)
    await async_session.commit()

    # Act
    await repository.log_audit_event(
        sample_offer.offer_id,
        "TEST_EVENT",
        {"key": "value"},
    )
    await async_session.commit()

    # Assert - event logged (verified by no exception)
