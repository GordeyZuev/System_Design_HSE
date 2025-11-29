# app/db.py
import hashlib
from typing import AsyncGenerator, Dict
from uuid import UUID

from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)
from sqlalchemy.orm import declarative_base

from app.settings import settings

Base = declarative_base()


def _load_shards_from_env() -> Dict[str, str]:
    shards = {}
    for key, value in vars(settings).items():
        if key.startswith("DB_URL_SHARD_"):
            shards[key.replace("DB_URL_", "").lower()] = value
    return shards


SHARDS = _load_shards_from_env()

_engines: Dict[str, any] = {}
_sessions: Dict[str, async_sessionmaker] = {}


def _init_shard(shard_name: str):
    if shard_name not in _engines:
        url = SHARDS[shard_name]
        print(f"[DB] Init engine for {shard_name}: {url}")
        engine = create_async_engine(url, future=True, echo=False)
        _engines[shard_name] = engine
        _sessions[shard_name] = async_sessionmaker(
            engine, expire_on_commit=False, class_=AsyncSession
        )


def _get_sessionmaker(shard_name: str) -> async_sessionmaker:
    _init_shard(shard_name)
    return _sessions[shard_name]


def _get_engine(shard_name: str):
    _init_shard(shard_name)
    return _engines[shard_name]


def pick_shard_by_user(user_id: UUID) -> str:
    h = hashlib.md5(user_id.bytes).hexdigest()
    shard_index = int(h, 16) % len(SHARDS)
    return f"shard_{shard_index}"
