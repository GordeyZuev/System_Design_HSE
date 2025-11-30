"""PostgreSQL repository implementation."""
import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import Offer, OfferStatus
from app.infrastructure.models import OfferAuditModel, OfferModel
from app.infrastructure.repositories import OfferRepository

logger = logging.getLogger(__name__)


class PostgresOfferRepository(OfferRepository):
    """PostgreSQL implementation of offer repository.
    
    Реализует абстрактный интерфейс OfferRepository,
    сохраняя чистую архитектуру и изоляцию слоев.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_domain(self, model: OfferModel) -> Offer:
        """Convert SQLAlchemy model to domain model."""
        return Offer(
            offer_id=model.offer_id,
            user_id=model.user_id,
            station_id=model.station_id,
            tariff_snapshot=model.tariff_snapshot,
            created_at=model.created_at,
            expires_at=model.expires_at,
            status=model.status,
            tariff_version=model.tariff_version,
        )

    def _to_model(self, offer: Offer) -> OfferModel:
        """Convert domain model to SQLAlchemy model."""
        return OfferModel(
            offer_id=offer.offer_id,
            user_id=offer.user_id,
            station_id=offer.station_id,
            tariff_snapshot=offer.tariff_snapshot,
            created_at=offer.created_at,
            expires_at=offer.expires_at,
            status=offer.status,
            tariff_version=offer.tariff_version,
        )

    async def create(self, offer: Offer) -> Offer:
        """Create a new offer."""
        model = self._to_model(offer)
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
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

        logger.info(f"Created offer {offer.offer_id} in database")
        await self.session.commit()
        return self._to_domain(model)

    async def get_by_id(self, offer_id: UUID) -> Optional[Offer]:
        """Get offer by ID."""
        stmt = select(OfferModel).where(OfferModel.offer_id == offer_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return self._to_domain(model)

    async def update_status(self, offer_id: UUID, status: OfferStatus) -> None:
        """Update offer status."""
        stmt = select(OfferModel).where(OfferModel.offer_id == offer_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        if model:
            old_status = model.status
            model.status = status
            await self.session.flush()

            # Log status change
            await self.log_audit_event(
                offer_id,
                "STATUS_CHANGED",
                {"old_status": old_status.value, "new_status": status.value},
            )

            logger.info(f"Updated offer {offer_id} status: {old_status} -> {status}")

    async def get_active_by_user(self, user_id: UUID) -> List[Offer]:
        """Get all active offers for a user."""
        stmt = (
            select(OfferModel)
            .where(
                OfferModel.user_id == user_id,
                OfferModel.status == OfferStatus.ACTIVE,
                OfferModel.expires_at > datetime.utcnow(),
            )
            .order_by(OfferModel.created_at.desc())
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()

        return [self._to_domain(model) for model in models]

    async def log_audit_event(
        self, offer_id: UUID, event_type: str, payload: dict
    ) -> None:
        """Log audit event."""
        audit = OfferAuditModel(
            offer_id=offer_id,
            event_type=event_type,
            ts=datetime.utcnow(),
            payload_json=payload,
        )
        self.session.add(audit)
        await self.session.flush()

        logger.debug(f"Logged audit event {event_type} for offer {offer_id}")

