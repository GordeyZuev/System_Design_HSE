from sqlalchemy import Column, String, Integer, DateTime, JSON, Enum, func, Numeric, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum
import uuid
from app.db.db import Base
from datetime import datetime

class RentalStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    FINISHED = "FINISHED"
    CANCELLED = "CANCELLED"

class OutboxStatus(str, enum.Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"

class Rental(Base):
    __tablename__ = "rentals"
    rental_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    offer_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    station_id = Column(String, nullable=False)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    finished_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(Enum(RentalStatus), nullable=False, default=RentalStatus.PENDING)
    tariff_snapshot = Column(JSON, nullable=False)
    tariff_version = Column(String, nullable=True)

class RentalEvent(Base):
    __tablename__ = "rental_events"
    event_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rental_id = Column(UUID(as_uuid=True), ForeignKey("rentals.rental_id", ondelete="CASCADE"), nullable=False, index=True)
    ts = Column(DateTime(timezone=True), server_default=func.now())
    type = Column(String, nullable=False)
    payload = Column(JSON, nullable=True)

class RentalCostSnapshot(Base):
    __tablename__ = "rental_cost_snapshots"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rental_id = Column(UUID(as_uuid=True), ForeignKey("rentals.rental_id", ondelete="CASCADE"), nullable=False, index=True)
    ts = Column(DateTime(timezone=True), server_default=func.now())
    cost_amount = Column(Numeric(10,2), nullable=False)
    details = Column(JSON, nullable=True)

class OutboxPayment(Base):
    __tablename__ = "payment_outbox"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    rental_id = Column(UUID)
    amount = Column(Numeric)
    created_at = Column(DateTime, default=datetime.utcnow)
    processed = Column(Boolean, default=False)
