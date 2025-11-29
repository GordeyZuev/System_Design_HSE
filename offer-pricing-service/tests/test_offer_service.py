"""Tests for OfferService."""
import pytest
from unittest.mock import AsyncMock
from uuid import UUID
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import (
    CreateOfferRequest,
    Offer,
    OfferStatus,
    UserSegment,
)
from app.domain.exceptions import (
    OfferNotFoundException,
    OfferExpiredException,
    OfferAlreadyUsedException,
    UserServiceUnavailableException,
)
from app.services.offer_service import OfferService
from app.infrastructure.repositories_postgres import PostgresOfferRepository


@pytest.mark.asyncio
async def test_create_offer_success(
    offer_service: OfferService,
    mock_user_id: UUID,
    mock_station_id: str,
) -> None:
    """Test successful offer creation."""
    # Arrange
    request = CreateOfferRequest(
        user_id=mock_user_id,
        station_id=mock_station_id,
        user_segment=UserSegment.STANDARD,
    )

    # Act
    response = await offer_service.create_offer(request)

    # Assert
    assert response.offer_id is not None
    assert response.expires_at > datetime.utcnow()
    assert response.estimated_rate_per_minute == 5.0
    assert response.currency == "RUB"
    assert "tariff_id" in response.tariff_details


@pytest.mark.asyncio
async def test_create_offer_without_segment(
    offer_service: OfferService,
    mock_user_id: UUID,
    mock_station_id: str,
    mock_user_client: AsyncMock,
) -> None:
    """Test offer creation without provided segment (fetches from User Service)."""
    # Arrange
    request = CreateOfferRequest(
        user_id=mock_user_id,
        station_id=mock_station_id,
        user_segment=None,  # Должен получить от User Service
    )

    # Act
    response = await offer_service.create_offer(request)

    # Assert
    assert response.offer_id is not None
    mock_user_client.get_user_segment.assert_called_once_with(mock_user_id)


@pytest.mark.asyncio
async def test_create_offer_greedy_pricing_fallback(
    offer_service: OfferService,
    mock_user_id: UUID,
    mock_station_id: str,
    mock_user_client: AsyncMock,
    mock_tariff_client: AsyncMock,
) -> None:
    """Test greedy pricing when User Service is unavailable."""
    # Arrange
    request = CreateOfferRequest(
        user_id=mock_user_id,
        station_id=mock_station_id,
        user_segment=None,
    )
    
    # Simulate User Service unavailability
    mock_user_client.get_user_segment = AsyncMock(
        side_effect=UserServiceUnavailableException()
    )

    # Act
    response = await offer_service.create_offer(request)

    # Assert
    assert response.offer_id is not None
    assert response.tariff_details["is_greedy"] is True
    assert response.estimated_rate_per_minute == 22.5  # 15.0 * 1.5
    mock_tariff_client.get_greedy_tariff.assert_called_once()


@pytest.mark.asyncio
async def test_get_offer_success(
    offer_service: OfferService,
    repository: PostgresOfferRepository,
    sample_offer: Offer,
    async_session: AsyncSession,
) -> None:
    """Test successful offer retrieval."""
    # Arrange
    await repository.create(sample_offer)
    await async_session.commit()

    # Act
    response = await offer_service.get_offer(sample_offer.offer_id)

    # Assert
    assert response.offer_id == sample_offer.offer_id
    assert response.user_id == sample_offer.user_id
    assert response.station_id == sample_offer.station_id
    assert response.is_valid is True


@pytest.mark.asyncio
async def test_get_offer_not_found(
    offer_service: OfferService,
    mock_offer_id: UUID,
) -> None:
    """Test offer not found."""
    # Act & Assert
    with pytest.raises(OfferNotFoundException):
        await offer_service.get_offer(mock_offer_id)


@pytest.mark.asyncio
async def test_get_offer_with_wrong_user(
    offer_service: OfferService,
    repository: PostgresOfferRepository,
    sample_offer: Offer,
    mock_user_id: UUID,
    async_session: AsyncSession,
) -> None:
    """Test offer retrieval with wrong user ID."""
    # Arrange
    await repository.create(sample_offer)
    await async_session.commit()
    wrong_user_id = UUID("00000000-0000-0000-0000-000000000001")

    # Act & Assert
    with pytest.raises(OfferNotFoundException):
        await offer_service.get_offer(sample_offer.offer_id, wrong_user_id)


@pytest.mark.asyncio
async def test_validate_and_use_offer_success(
    offer_service: OfferService,
    repository: PostgresOfferRepository,
    sample_offer: Offer,
    async_session: AsyncSession,
) -> None:
    """Test successful offer validation and usage."""
    # Arrange
    await repository.create(sample_offer)
    await async_session.commit()

    # Act
    result = await offer_service.validate_and_use_offer(
        sample_offer.offer_id,
        sample_offer.user_id,
    )
    await async_session.commit()

    # Assert
    assert result.offer_id == sample_offer.offer_id
    
    # Verify status was updated
    updated_offer = await repository.get_by_id(sample_offer.offer_id)
    assert updated_offer.status == OfferStatus.USED


@pytest.mark.asyncio
async def test_validate_expired_offer(
    offer_service: OfferService,
    repository: PostgresOfferRepository,
    sample_offer: Offer,
    async_session: AsyncSession,
) -> None:
    """Test validation of expired offer."""
    # Arrange
    sample_offer.expires_at = datetime.utcnow() - timedelta(minutes=1)
    await repository.create(sample_offer)
    await async_session.commit()

    # Act & Assert
    with pytest.raises(OfferExpiredException):
        await offer_service.validate_and_use_offer(
            sample_offer.offer_id,
            sample_offer.user_id,
        )


@pytest.mark.asyncio
async def test_validate_already_used_offer(
    offer_service: OfferService,
    repository: PostgresOfferRepository,
    sample_offer: Offer,
    async_session: AsyncSession,
) -> None:
    """Test validation of already used offer."""
    # Arrange
    sample_offer.status = OfferStatus.USED
    await repository.create(sample_offer)
    await async_session.commit()

    # Act & Assert
    with pytest.raises(OfferAlreadyUsedException):
        await offer_service.validate_and_use_offer(
            sample_offer.offer_id,
            sample_offer.user_id,
        )


@pytest.mark.asyncio
async def test_validate_offer_wrong_user(
    offer_service: OfferService,
    repository: PostgresOfferRepository,
    sample_offer: Offer,
    async_session: AsyncSession,
) -> None:
    """Test validation with wrong user."""
    # Arrange
    await repository.create(sample_offer)
    await async_session.commit()
    wrong_user_id = UUID("00000000-0000-0000-0000-000000000001")

    # Act & Assert
    with pytest.raises(OfferNotFoundException):
        await offer_service.validate_and_use_offer(
            sample_offer.offer_id,
            wrong_user_id,
        )

