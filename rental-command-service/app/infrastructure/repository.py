from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain import models
from uuid import UUID
from decimal import Decimal
from datetime import datetime

class RentalRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_offer_id_active(self, offer_id: UUID):
        q = select(models.Rental).where(models.Rental.offer_id == offer_id, models.Rental.status == models.RentalStatus.ACTIVE)
        res = await self.session.execute(q)
        return res.scalars().first()
    
    async def get_by_user_id(self, user_id: UUID):
        q = select(models.Rental).where(models.Rental.user_id == user_id, models.Rental.status == models.RentalStatus.ACTIVE)
        res = await self.session.execute(q)
        return res.scalars().first()

    async def create_rental(self, offer_id: UUID, user_id: UUID, station_id: str, tariff_snapshot: dict, tariff_version: str):
        r = models.Rental(
            offer_id=offer_id,
            user_id=user_id,
            station_id=station_id,
            status=models.RentalStatus.ACTIVE,
            tariff_snapshot=tariff_snapshot,
            tariff_version=tariff_version
        )
        self.session.add(r)
        await self.session.flush()
        return r

    async def finish_rental(self, rental_id: UUID, finish_time: datetime, final_cost: Decimal):
        q = select(models.Rental).where(models.Rental.rental_id == rental_id)
        res = await self.session.execute(q)
        r = res.scalars().first()
        if not r:
            return None
        r.finished_at = finish_time
        r.status = models.RentalStatus.FINISHED
        self.session.add(r)
        snap = models.RentalCostSnapshot(rental_id=r.rental_id, cost_amount=final_cost, details={})
        
        self.session.add(snap)
        await self.session.flush()
        return r

    async def get(self, rental_id: UUID):
        q = select(models.Rental).where(models.Rental.rental_id == rental_id)
        res = await self.session.execute(q)
        return res.scalars().first()

    async def insert_event(self, rental_id: UUID, event_type: str, payload: dict):
        
        ev = models.RentalEvent(rental_id=rental_id, type=event_type, payload=payload)
        self.session.add(ev)
        await self.session.flush()
        return ev
    
    async def create_outbox_payment(self, rental_id: UUID, amount: Decimal):
        ev = models.OutboxPayment(
            rental_id=rental_id,
            amount=amount,
        )
        self.session.add(ev)
        await self.session.flush()
        return ev
    

