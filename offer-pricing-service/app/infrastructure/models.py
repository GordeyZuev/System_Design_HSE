"""SQLAlchemy ORM models for database tables."""
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, Index, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID as PostgreSQL_UUID
from sqlalchemy.types import TypeDecorator, CHAR

from app.domain.models import OfferStatus
from app.infrastructure.database import Base


class GUID(TypeDecorator):
    """Platform-independent GUID type.
    
    Uses PostgreSQL UUID, otherwise CHAR(32), storing as stringified hex.
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PostgreSQL_UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(32))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return "%.32x" % uuid.UUID(value).int
            else:
                return "%.32x" % value.int

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                value = uuid.UUID(value)
            return value


class OfferModel(Base):
    """SQLAlchemy model for offers table."""

    __tablename__ = "offers"

    offer_id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID(), nullable=False, index=True)
    station_id = Column(String(255), nullable=False, index=True)
    tariff_snapshot = Column(JSON, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    status = Column(
        Enum(OfferStatus, name="offer_status"),
        nullable=False,
        default=OfferStatus.ACTIVE,
        index=True,
    )
    tariff_version = Column(String(50), nullable=True)

    # Composite indexes for common queries
    __table_args__ = (
        Index("idx_offers_user_status", "user_id", "status"),
        Index("idx_offers_status_expires", "status", "expires_at"),
    )


class OfferAuditModel(Base):
    """SQLAlchemy model for offer audit log."""

    __tablename__ = "offer_audit"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    offer_id = Column(GUID(), nullable=False, index=True)
    event_type = Column(String(50), nullable=False)
    ts = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    payload_json = Column(JSON, nullable=True)

    __table_args__ = (Index("idx_audit_offer_ts", "offer_id", "ts"),)
