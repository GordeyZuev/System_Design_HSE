import hashlib
from typing import AsyncGenerator, Dict, Optional
from uuid import UUID

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)
from sqlalchemy.orm import declarative_base

from app.db.db import _get_sessionmaker, pick_shard_by_user
from app.infrastructure.clients.config_client import ConfigClient
from app.infrastructure.clients.offer_client import OfferClient
from app.infrastructure.clients.payments_adapter_client import PaymentsAdapter
from app.infrastructure.clients.stations_adapter_client import StationsAdapter
from app.infrastructure.repository import RentalRepository
from app.services.rental_service import RentalService
from app.settings import settings

_config_client: Optional[ConfigClient] = None
_offer_client: Optional[OfferClient] = None
_payments_adapter: Optional[PaymentsAdapter] = None
_stations_adapter: Optional[StationsAdapter] = None
_rental_command_repository: Optional[RentalRepository] = None


async def get_config_client() -> ConfigClient:
    global _config_client
    if _config_client is None:
        _config_client = ConfigClient(url="http://fake-config")
        _config_client._cache = {
            "offer_service_url": settings.OFFER_SERVICE_URL,
            "stations_adapter_url": settings.STATIONS_SERVICE_URL,
            "payments_adapter_url": settings.PAYMENTS_SERVICE_URL,
        }
        _config_client._expires_at = 9999999999
    return _config_client


async def get_offer_client() -> OfferClient:
    global _offer_client
    if _offer_client is None:
        config_client = await get_config_client()
        _offer_client = OfferClient(config_client)
    return _offer_client


async def get_payments_adapter():
    global _payments_adapter
    if _payments_adapter is None:
        config_client = await get_config_client()
        _payments_adapter = PaymentsAdapter(config_client)
    return _payments_adapter


async def get_stations_adapter():
    global _stations_adapter
    if _stations_adapter is None:
        config_client = await get_config_client()
        _stations_adapter = StationsAdapter(config_client)
    return _stations_adapter


async def get_db(user_id: UUID):
    shard_name = pick_shard_by_user(user_id)
    SessionLocal = _get_sessionmaker(shard_name)
    async with SessionLocal() as session:
        yield session


def get_user_id(authorization: str = Header(None)) -> UUID:
    if not authorization:
        raise HTTPException(
            status_code=401, detail="Missing Authorization header"
        )

    try:
        token = authorization.replace("Bearer", "").strip()
        return UUID(token)
    except Exception:
        raise HTTPException(
            status_code=401, detail="Invalid Authorization header"
        )


async def get_sharded_db(user_id: UUID = Depends(get_user_id)):
    async for session in get_db(user_id):
        yield session


async def get_rental_command_repository(
    db: AsyncSession = Depends(get_sharded_db),
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
