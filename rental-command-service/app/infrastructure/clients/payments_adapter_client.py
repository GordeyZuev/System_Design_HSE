from typing import Any, Dict
import httpx
from tenacity import retry, stop_after_attempt, wait_fixed

from app.settings import settings


def _client():
    return httpx.AsyncClient(timeout=settings.HTTP_TIMEOUT_SECONDS)



class PaymentsAdapter:
    def __init__(self, cfg_client):
        self.cfg = cfg_client

    async def charge(self, rental_id: str, amount: float, metadata: Dict[str, Any]) -> Dict[str, Any]:
        cfg = await self.cfg.get_config()
        url = f"{cfg['payments_adapter_url'].rstrip('/')}/payments/charge"
        payload = {"rental_id": rental_id, "amount": amount, "metadata": metadata}
        async with _client() as c:
            r = await c.post(url, json=payload)
            r.raise_for_status()
            return r.json()
