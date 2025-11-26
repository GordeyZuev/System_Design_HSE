"""Offer Service implementation."""
import logging
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from app.config import settings
from app.domain.exceptions import (
    OfferAlreadyUsedException,
    OfferExpiredException,
    OfferNotFoundException,
    UserServiceUnavailableException,
)
from app.domain.models import (
    CreateOfferRequest,
    CreateOfferResponse,
    GetOfferResponse,
    Offer,
    OfferStatus,
    UserSegment,
)
from app.infrastructure.clients import ConfigClient, TariffClient, UserClient
from app.infrastructure.repositories import OfferRepository

logger = logging.getLogger(__name__)


class OfferService:
    """Service for managing offers and pricing."""

    def __init__(
        self,
        offer_repository: OfferRepository,
        tariff_client: TariffClient,
        user_client: UserClient,
        config_client: ConfigClient,
    ):
        self.offer_repository = offer_repository
        self.tariff_client = tariff_client
        self.user_client = user_client
        self.config_client = config_client

    async def create_offer(self, request: CreateOfferRequest) -> CreateOfferResponse:
        """Create a new offer with pricing calculation.

        Реализует greedy pricing fallback при недоступности User Service.
        """
        logger.info(
            f"Creating offer for user {request.user_id} at station {request.station_id}"
        )

        # Get configuration
        config = await self.config_client.get_config()

        # Determine user segment
        user_segment = request.user_segment
        use_greedy_pricing = False

        if user_segment is None:
            try:
                # Try to get user segment from User Service
                user_segment = await self.user_client.get_user_segment(request.user_id)
                logger.info(f"Got user segment from User Service: {user_segment}")
            except UserServiceUnavailableException:
                logger.warning(
                    f"User Service unavailable for user {request.user_id}, "
                    "using greedy pricing"
                )
                use_greedy_pricing = True

        # Get tariff information
        if use_greedy_pricing:
            tariff_info = await self.tariff_client.get_greedy_tariff(request.station_id)
            logger.info("Using greedy tariff due to User Service unavailability")
        else:
            tariff_info = await self.tariff_client.get_tariff(
                request.station_id, user_segment
            )
            logger.info(f"Using regular tariff for segment {user_segment}")

        # Calculate offer expiration
        expires_at = datetime.utcnow() + timedelta(
            seconds=config.offer_ttl or settings.offer_default_ttl
        )

        # Create tariff snapshot
        tariff_snapshot = {
            "tariff_id": tariff_info.tariff_id,
            "base_rate": tariff_info.base_rate,
            "segment_multiplier": tariff_info.segment_multiplier,
            "currency": tariff_info.currency,
            "rules": tariff_info.rules,
            "segment": user_segment.value if user_segment else "GREEDY",
            "is_greedy": use_greedy_pricing,
        }

        # Create offer
        offer = Offer(
            user_id=request.user_id,
            station_id=request.station_id,
            tariff_snapshot=tariff_snapshot,
            expires_at=expires_at,
            status=OfferStatus.ACTIVE,
            tariff_version=tariff_info.version,
        )

        # Save to repository
        created_offer = await self.offer_repository.create(offer)

        logger.info(f"Created offer {created_offer.offer_id}")

        # Calculate estimated rate
        estimated_rate = tariff_info.base_rate * tariff_info.segment_multiplier

        return CreateOfferResponse(
            offer_id=created_offer.offer_id,
            expires_at=created_offer.expires_at,
            tariff_details=tariff_snapshot,
            estimated_rate_per_minute=estimated_rate,
            currency=tariff_info.currency,
        )

    async def get_offer(self, offer_id: UUID, user_id: Optional[UUID] = None) -> GetOfferResponse:
        """Get offer by ID with validation."""
        logger.info(f"Getting offer {offer_id}")

        offer = await self.offer_repository.get_by_id(offer_id)

        if offer is None:
            raise OfferNotFoundException(str(offer_id))

        # Check ownership if user_id provided
        if user_id is not None and offer.user_id != user_id:
            raise OfferNotFoundException(str(offer_id))

        # Check if offer is valid
        is_valid = self._is_offer_valid(offer)

        return GetOfferResponse(
            offer_id=offer.offer_id,
            user_id=offer.user_id,
            station_id=offer.station_id,
            status=offer.status,
            created_at=offer.created_at,
            expires_at=offer.expires_at,
            tariff_snapshot=offer.tariff_snapshot,
            is_valid=is_valid,
        )

    async def validate_and_use_offer(self, offer_id: UUID, user_id: UUID) -> Offer:
        """Validate offer and mark as used.

        Используется Rental Command Service при старте аренды.
        """
        logger.info(f"Validating and using offer {offer_id} for user {user_id}")

        offer = await self.offer_repository.get_by_id(offer_id)

        if offer is None:
            raise OfferNotFoundException(str(offer_id))

        # Check ownership
        if offer.user_id != user_id:
            raise OfferNotFoundException(str(offer_id))

        # Check status
        if offer.status == OfferStatus.USED:
            raise OfferAlreadyUsedException(str(offer_id))

        if offer.status != OfferStatus.ACTIVE:
            raise OfferExpiredException(str(offer_id))

        # Check expiration
        if not self._is_offer_valid(offer):
            await self.offer_repository.update_status(offer_id, OfferStatus.EXPIRED)
            raise OfferExpiredException(str(offer_id))

        # Mark as used
        await self.offer_repository.update_status(offer_id, OfferStatus.USED)

        logger.info(f"Offer {offer_id} validated and marked as USED")

        return offer

    def _is_offer_valid(self, offer: Offer) -> bool:
        """Check if offer is valid (not expired and active)."""
        return (
            offer.status == OfferStatus.ACTIVE
            and offer.expires_at > datetime.utcnow()
        )

