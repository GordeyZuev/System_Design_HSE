from typing import Any, Dict
import httpx
from tenacity import retry, stop_after_attempt, wait_fixed
from app.settings import settings


def _client():
    return httpx.AsyncClient(timeout=settings.HTTP_TIMEOUT_SECONDS)



class StationsAdapter:
    def __init__(self, cfg_client):
        self.cfg = cfg_client
        self._retries = settings.STATIONS_RETRY

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def reserve_or_issue(self, station_id: str, user_id: str) -> Dict[str, Any]:
        cfg = await self.cfg.get_config()
        url = f"{cfg['stations_adapter_url'].rstrip('/')}/stations/reserve_or_issue"
        payload = {"station_id": station_id, "user_id": user_id}
        async with _client() as c:
            r = await c.post(url, json=payload)
            r.raise_for_status()
            return r.json()

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def return_powerbank(self, station_id: str, rental_id: str) -> Dict[str, Any]:
        cfg = await self.cfg.get_config()
        url = f"{cfg['stations_adapter_url'].rstrip('/')}/stations/return"
        payload = {"station_id": station_id, "rental_id": rental_id}
        async with _client() as c:
            r = await c.post(url, json=payload)
            r.raise_for_status()
            return r.json()