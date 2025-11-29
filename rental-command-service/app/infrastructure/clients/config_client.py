import time
from typing import Any, Dict

import httpx
from fastapi import HTTPException
from tenacity import retry, stop_after_attempt, wait_fixed

from app.settings import settings


class ConfigClient:

    def __init__(
        self,
        url: str = settings.CONFIG_SERVICE_URL,
        ttl: int = settings.CONFIG_TTL_SECONDS,
    ):
        self.url = str(url).rstrip("/")
        self.ttl = ttl
        self._cache: Dict[str, Any] = {}
        self._expires_at: float = 0.0

    def _is_valid(self) -> bool:
        return bool(self._cache) and time.time() < self._expires_at

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def _fetch_remote(self) -> Dict[str, Any]:
        async with httpx.AsyncClient(
            timeout=settings.HTTP_TIMEOUT_SECONDS
        ) as client:
            resp = await client.get(self.url)
            resp.raise_for_status()
            return resp.json()

    async def get_config(self) -> Dict[str, Any]:
        if self._is_valid():
            return self._cache

        try:
            data = await self._fetch_remote()
            required = [
                "offer_service_url",
                "stations_adapter_url",
                "payments_adapter_url",
            ]
            for key in required:
                if key not in data:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Config missing required key: {key}",
                    )
            self._cache = data
            self._expires_at = time.time() + self.ttl
        except Exception:
            if not self._cache:
                raise HTTPException(
                    status_code=503,
                    detail="Config Service unavailable and no cached config",
                )

        return self._cache
