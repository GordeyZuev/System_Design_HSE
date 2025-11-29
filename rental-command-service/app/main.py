import asyncio

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api import monitoring, routes
from app.db.db import SHARDS, Base, _engines, _get_engine
from app.domain.exception import DomainException

app = FastAPI(title="Rental Command Service")

app.include_router(routes.router)
app.include_router(monitoring.router)


@app.on_event("startup")
async def startup_event():
    for shard_name in SHARDS:
        if shard_name not in _engines:
            _get_engine(shard_name)
        engine = _engines[shard_name]
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
