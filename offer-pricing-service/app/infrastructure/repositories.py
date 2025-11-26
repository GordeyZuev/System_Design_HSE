"""Abstract repository interface."""
from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from app.domain.models import Offer, OfferStatus


class OfferRepository(ABC):
    """Abstract offer repository interface."""

    @abstractmethod
    async def create(self, offer: Offer) -> Offer:
        """Create a new offer."""
        pass

    @abstractmethod
    async def get_by_id(self, offer_id: UUID) -> Optional[Offer]:
        """Get offer by ID."""
        pass

    @abstractmethod
    async def update_status(self, offer_id: UUID, status: OfferStatus) -> None:
        """Update offer status."""
        pass

    @abstractmethod
    async def get_active_by_user(self, user_id: UUID) -> List[Offer]:
        """Get all active offers for a user."""
        pass

    @abstractmethod
    async def log_audit_event(
        self, offer_id: UUID, event_type: str, payload: dict
    ) -> None:
        """Log audit event."""
        pass

