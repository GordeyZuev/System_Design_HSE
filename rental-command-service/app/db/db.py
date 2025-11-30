# app/db.py
import hashlib
from typing import AsyncGenerator, Dict
from uuid import UUID

from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)
from sqlalchemy.orm import declarative_base

from app.settings import settings

Base = declarative_base()

SHARDS = {
    "shard_0": settings.DB_URL_SHARD_0,
    "shard_1": settings.DB_URL_SHARD_1,
}

REPLICAS = {
    "shard_0": settings.DB_URL_SHARD_0_REPLICA,
    "shard_1": settings.DB_URL_SHARD_1_REPLICA,
}

_engines: Dict[str, any] = {}
_sessions: Dict[str, async_sessionmaker] = {}


def _init_engine(url: str):
    return create_async_engine(url, future=True, echo=False)

def _init_shard(shard_name: str):
    if shard_name not in _engines:
        master_url = SHARDS[shard_name]
        replica_url = REPLICAS.get(shard_name)

        _engines[shard_name] = _init_engine(master_url)
        _sessions[shard_name] = async_sessionmaker(
            _engines[shard_name], expire_on_commit=False, class_=AsyncSession
        )

        if replica_url:
            _engines[f"{shard_name}_replica"] = _init_engine(replica_url)
            _sessions[f"{shard_name}_replica"] = async_sessionmaker(
                _engines[f"{shard_name}_replica"], expire_on_commit=False, class_=AsyncSession
            )


def pick_shard_by_user(user_id: UUID) -> str:

    h = hashlib.md5(user_id.bytes).hexdigest()
    shard_index = int(h, 16) % len(SHARDS)
    return f"shard_{shard_index}"

def get_sessionmaker(user_id: UUID, use_replica: bool = False) -> async_sessionmaker:
    shard_name = pick_shard_by_user(user_id)
    if use_replica:
        shard_name = f"{shard_name}_replica"
    _init_shard(shard_name.replace("_replica", ""))
    return _sessions[shard_name]


async def get_db(user_id: UUID, use_replica: bool = False) -> AsyncGenerator[AsyncSession, None]:
    session_maker = get_sessionmaker(user_id, use_replica)
    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
