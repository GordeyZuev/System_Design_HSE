"""API routes."""
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from prometheus_client import Counter, Histogram

from app.domain.exceptions import (
    DomainException,
    OfferAlreadyUsedException,
    OfferExpiredException,
    OfferNotFoundException,
    TariffServiceUnavailableException,
)
from app.domain.models import CreateOfferRequest, CreateOfferResponse, GetOfferResponse
from app.services.offer_service import OfferService

from .dependencies import get_offer_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal/offers", tags=["offers"])

# Prometheus metrics
offer_created_counter = Counter(
    "offer_created_total", "Total number of offers created", ["status"]
)
offer_get_counter = Counter(
    "offer_get_total", "Total number of offer retrievals", ["status"]
)
offer_validate_counter = Counter(
    "offer_validate_total", "Total number of offer validations", ["status"]
)
offer_creation_duration = Histogram(
    "offer_creation_duration_seconds", "Time spent creating offers"
)


@router.post("", response_model=CreateOfferResponse, status_code=status.HTTP_201_CREATED)
async def create_offer(
    request: CreateOfferRequest,
    service: OfferService = Depends(get_offer_service),
) -> CreateOfferResponse:
    """Create a new offer.

    Endpoint для создания оффера с прайсингом.
    Используется API Gateway при запросе от клиента.
    """
    try:
        with offer_creation_duration.time():
            response = await service.create_offer(request)
        offer_created_counter.labels(status="success").inc()
        return response
    except TariffServiceUnavailableException as e:
        logger.error(f"Tariff service unavailable: {e}")
        offer_created_counter.labels(status="tariff_unavailable").inc()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": e.code, "message": e.message},
        )
    except DomainException as e:
        logger.error(f"Domain error creating offer: {e}")
        offer_created_counter.labels(status="error").inc()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": e.code, "message": e.message},
        )
    except Exception as e:
        logger.exception(f"Unexpected error creating offer: {e}")
        offer_created_counter.labels(status="internal_error").inc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "INTERNAL_ERROR", "message": "Internal server error"},
        )


@router.get("/{offer_id}", response_model=GetOfferResponse)
async def get_offer(
    offer_id: UUID,
    user_id: Optional[UUID] = None,
    service: OfferService = Depends(get_offer_service),
) -> GetOfferResponse:
    """Get offer by ID.

    Endpoint для получения информации об оффере.
    Используется для проверки состояния оффера.
    """
    try:
        response = await service.get_offer(offer_id, user_id)
        offer_get_counter.labels(status="success").inc()
        return response
    except OfferNotFoundException as e:
        logger.warning(f"Offer not found: {e}")
        offer_get_counter.labels(status="not_found").inc()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": e.code, "message": e.message},
        )
    except Exception as e:
        logger.exception(f"Unexpected error getting offer: {e}")
        offer_get_counter.labels(status="error").inc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "INTERNAL_ERROR", "message": "Internal server error"},
        )


@router.post("/{offer_id}/validate", status_code=status.HTTP_200_OK)
async def validate_offer(
    offer_id: UUID,
    user_id: UUID,
    service: OfferService = Depends(get_offer_service),
) -> dict:
    """Validate and use offer.

    Endpoint для валидации и использования оффера при старте аренды.
    Используется Rental Command Service.
    """
    try:
        offer = await service.validate_and_use_offer(offer_id, user_id)
        offer_validate_counter.labels(status="success").inc()
        return {
            "offer_id": str(offer.offer_id),
            "status": "VALIDATED",
            "tariff_snapshot": offer.tariff_snapshot,
            "expires_at": offer.expires_at,
            "user_id": str(offer.user_id),
            "tariff_version": offer.tariff_version,
            "station_id": offer.station_id
        }
    except OfferNotFoundException as e:
        logger.warning(f"Offer not found for validation: {e}")
        offer_validate_counter.labels(status="not_found").inc()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": e.code, "message": e.message},
        )
    except OfferExpiredException as e:
        logger.warning(f"Offer expired: {e}")
        offer_validate_counter.labels(status="expired").inc()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": e.code, "message": e.message},
        )
    except OfferAlreadyUsedException as e:
        logger.warning(f"Offer already used: {e}")
        offer_validate_counter.labels(status="already_used").inc()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": e.code, "message": e.message},
        )
    except Exception as e:
        logger.exception(f"Unexpected error validating offer: {e}")
        offer_validate_counter.labels(status="error").inc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "INTERNAL_ERROR", "message": "Internal server error"},
        )

