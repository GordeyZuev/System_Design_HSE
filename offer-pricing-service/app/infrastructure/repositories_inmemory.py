"""In-memory repository implementations for development/testing."""
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from app.domain.models import Offer, OfferStatus
from app.infrastructure.repositories import OfferRepository


class InMemoryOfferRepository(OfferRepository):
    """In-memory implementation of offer repository."""

    def __init__(self) -> None:
        self._offers: Dict[UUID, Offer] = {}
        self._audit_events: List[dict] = []

    async def create(self, offer: Offer) -> Offer:
        """Create a new offer."""
        self._offers[offer.offer_id] = offer

        # Log creation event
        await self.log_audit_event(
            offer.offer_id,
            "CREATED",
            {
                "user_id": str(offer.user_id),
                "station_id": offer.station_id,
                "expires_at": offer.expires_at.isoformat(),
            },
        )

        return offer

    async def get_by_id(self, offer_id: UUID) -> Optional[Offer]:
        """Get offer by ID."""
        return self._offers.get(offer_id)

    async def update_status(self, offer_id: UUID, status: OfferStatus) -> None:
        """Update offer status."""
        offer = self._offers.get(offer_id)

        if offer:
            old_status = offer.status
            offer.status = status

            # Log status change
            await self.log_audit_event(
                offer_id,
                "STATUS_CHANGED",
                {"old_status": old_status.value, "new_status": status.value},
            )

    async def get_active_by_user(self, user_id: UUID) -> List[Offer]:
        """Get all active offers for a user."""
        return [
            offer
            for offer in self._offers.values()
            if offer.user_id == user_id
            and offer.status == OfferStatus.ACTIVE
            and offer.expires_at > datetime.utcnow()
        ]

    async def log_audit_event(
        self, offer_id: UUID, event_type: str, payload: dict
    ) -> None:
        """Log audit event."""
        self._audit_events.append(
            {
                "offer_id": offer_id,
                "event_type": event_type,
                "ts": datetime.utcnow(),
                "payload": payload,
            }
        )

    def clear(self) -> None:
        """Clear all data (for testing)."""
        self._offers.clear()
        self._audit_events.clear()

