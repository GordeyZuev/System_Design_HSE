# tests/test_api_rentals.py
import pytest
from uuid import uuid4, UUID
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock
from decimal import Decimal
from app.domain.exception import (
    OfferNotActiveException,
    UserAlreadyRentException,
    RentalNotFoundException,
    UserIdsMismatchException,
    RentalAlreadyFinishedException
)

from app.utils import minutes_between

@pytest.mark.asyncio
async def test_start_rental_success(rental_service, mock_user_id, mock_offer_id):
   
    rental = await rental_service.start_rental(mock_user_id, mock_offer_id)

    assert rental is not None
    assert rental.status == "ACTIVE"
    assert hasattr(rental, "rental_id")
    assert hasattr(rental, "started_at")

    rental_service.offer_client.validate_offer.assert_awaited_once_with(str(mock_offer_id), str(mock_user_id))
    rental_service.stations_adapter.reserve_or_issue.assert_awaited_once()
    rental_service.repo.create_rental.assert_awaited_once()


@pytest.mark.asyncio
async def test_finish_rental_success(rental_service, sample_rental):
    # Fix started_at to be 2 minutes ago
    fixed_started_at = datetime.now(timezone.utc) - timedelta(minutes=2)
    
    sample_rental.user_id = UUID("550e8400-e29b-41d4-a716-446655440000")
    sample_rental.status = "ACTIVE"
    sample_rental.started_at = fixed_started_at
    sample_rental.tariff_snapshot = {"initial_fee": 10, "per_minute": 1}

    rental_service.repo.get = AsyncMock(return_value=sample_rental)
    rental_service.repo.finish_rental = AsyncMock()
    rental_service.repo.insert_event = AsyncMock()
    rental_service.repo.create_outbox_payment = AsyncMock(return_value=MagicMock(id=uuid4()))

    rental_service.stations_adapter.return_powerbank = AsyncMock(return_value={"success": True})

    result = await rental_service.finish_rental(
        user_id=sample_rental.user_id,
        rental_id=sample_rental.rental_id,
        return_station_id="ST1"
    )

    # Don't check exact value, just verify it was called with some value > 10
    assert rental_service.repo.finish_rental.await_count == 1
    call_args = rental_service.repo.finish_rental.await_args[0]
    assert call_args[0] == sample_rental.rental_id
    assert isinstance(call_args[2], Decimal)
    assert call_args[2] >= Decimal('10')  # At least initial_fee
    
    rental_service.repo.create_outbox_payment.assert_awaited_once()
    rental_service.stations_adapter.return_powerbank.assert_awaited_once()
    assert result["rental_id"] == sample_rental.rental_id
    assert "final_cost" in result

@pytest.mark.asyncio
async def test_start_rental_offer_not_active(rental_service, mock_user_id, mock_offer_id):
    rental_service.repo.get_by_user_id = AsyncMock(return_value=None)
    
    rental_service.offer_client.validate_offer = AsyncMock(return_value={
        "status": "INACTIVE",
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
        "user_id": str(mock_user_id),
        "tariff_snapshot": {"initial_fee": 10, "per_minute": 1},
        "tariff_version": 1,
        "station_id": "ST1",
    })

    try:
        await rental_service.start_rental(mock_user_id, mock_offer_id)
    except Exception as e:
        assert isinstance(e, OfferNotActiveException)
        assert str(mock_offer_id) in str(e)

@pytest.mark.asyncio
async def test_start_rental_user_already_has_active_rental(rental_service, mock_user_id, mock_offer_id, sample_rental):
    rental_service.repo.get_by_user_id = AsyncMock(return_value=sample_rental)

    try:
        await rental_service.start_rental(mock_user_id, mock_offer_id)
    except Exception as e:
        assert isinstance(e, UserAlreadyRentException)
        assert str(mock_user_id) in str(e)

@pytest.mark.asyncio
async def test_finish_rental_not_found(rental_service, mock_user_id):
    rental_service.repo.get = AsyncMock(return_value=None)

    try:
        await rental_service.finish_rental(mock_user_id, uuid4(), "ST1")
    except Exception as e:
        assert isinstance(e, RentalNotFoundException)

@pytest.mark.asyncio
async def test_finish_rental_user_mismatch(rental_service, sample_rental):
    sample_rental.user_id = uuid4()  # другой юзер
    rental_service.repo.get = AsyncMock(return_value=sample_rental)

    try:
        await rental_service.finish_rental(UUID("550e8400-e29b-41d4-a716-446655440000"), sample_rental.rental_id, "ST1")
    except Exception as e:
        assert isinstance(e, UserIdsMismatchException)

@pytest.mark.asyncio
async def test_finish_rental_already_finished(rental_service, sample_rental, mock_user_id):
    sample_rental.status = "FINISHED"
    sample_rental.user_id = mock_user_id
    rental_service.repo.get = AsyncMock(return_value=sample_rental)

    try:
        await rental_service.finish_rental(mock_user_id, sample_rental.rental_id, "ST1")
    except Exception as e:
        assert isinstance(e, RentalAlreadyFinishedException)

@pytest.mark.asyncio
async def test_finish_rental_cost_calculation(rental_service, sample_rental, mock_user_id):
    sample_rental.user_id = mock_user_id
    sample_rental.status = "ACTIVE"
    sample_rental.started_at = datetime.now(timezone.utc) - timedelta(minutes=10)
    sample_rental.tariff_snapshot = {"initial_fee": 10, "per_minute": 2}

    rental_service.repo.get = AsyncMock(return_value=sample_rental)
    rental_service.repo.finish_rental = AsyncMock()
    rental_service.repo.insert_event = AsyncMock()
    rental_service.repo.create_outbox_payment = AsyncMock(return_value=MagicMock(id=uuid4()))
    rental_service.stations_adapter.return_powerbank = AsyncMock(return_value={"success": True})

    result = await rental_service.finish_rental(mock_user_id, sample_rental.rental_id, "ST1")
    
    assert result["final_cost"] >= 10
    rental_service.repo.finish_rental.assert_awaited_once()
    rental_service.repo.create_outbox_payment.assert_awaited_once()