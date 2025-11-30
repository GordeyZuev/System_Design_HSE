import hashlib
from typing import AsyncGenerator, Dict, Optional
from uuid import UUID

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)
from sqlalchemy.orm import declarative_base

from app.db.db import get_db
from app.infrastructure.clients.offer_client import OfferClient
from app.infrastructure.clients.payments_adapter_client import PaymentsAdapter
from app.infrastructure.clients.stations_adapter_client import StationsAdapter
from app.infrastructure.repository import RentalRepository
from app.services.rental_service import RentalService
from app.settings import settings

_offer_client: Optional[OfferClient] = None
_payments_adapter: Optional[PaymentsAdapter] = None
_stations_adapter: Optional[StationsAdapter] = None
_rental_command_repository: Optional[RentalRepository] = None



async def get_offer_client() -> OfferClient:
    global _offer_client
    if _offer_client is None:
        _offer_client = OfferClient()
    return _offer_client


async def get_payments_adapter():
    global _payments_adapter
    if _payments_adapter is None:
        _payments_adapter = PaymentsAdapter()
    return _payments_adapter


async def get_stations_adapter():
    global _stations_adapter
    if _stations_adapter is None:
        _stations_adapter = StationsAdapter()
    return _stations_adapter



def get_user_id(authorization: str = Header(None)) -> UUID:
    if not authorization:
        raise HTTPException(
            status_code=401, detail="Missing Authorization header"
        )

    try:
        token = authorization
        return UUID(token)
    except Exception:
        raise HTTPException(
            status_code=401, detail="Invalid Authorization header"
        )


async def get_sharded_db(
    user_id: UUID = Depends(get_user_id), 
    use_replica: bool = False
)-> AsyncGenerator[AsyncSession, None]:
    async for session in get_db(user_id, use_replica):
        yield session


async def get_sharded_db_replica(
    user_id: UUID = Depends(get_user_id), 
    use_replica: bool = True
)-> AsyncGenerator[AsyncSession, None]:
    async for session in get_db(user_id, use_replica):
        yield session


async def get_rental_command_repository(
    db: AsyncSession = Depends(get_sharded_db),
) -> RentalRepository:
    return RentalRepository(db)

async def get_rental_command_repository_replica(
    db: AsyncSession = Depends(get_sharded_db_replica)
) -> RentalRepository:
    return RentalRepository(db)


async def get_rental_command_service(
    repo: RentalRepository = Depends(get_rental_command_repository),
    offer_client=Depends(get_offer_client),
    stations_adapter=Depends(get_stations_adapter),
) -> RentalService:

    return RentalService(
        session=repo.session,
        offer_client=offer_client,
        stations_adapter=stations_adapter,
    )

async def get_rental_command_service_replica(
    repo: RentalRepository = Depends(get_rental_command_repository_replica),
    offer_client=Depends(get_offer_client),
    stations_adapter=Depends(get_stations_adapter),
) -> RentalService:
    return RentalService(
        session=repo.session,
        offer_client=offer_client,
        stations_adapter=stations_adapter,
    )
