from typing import Any, Dict

import httpx
from tenacity import retry, stop_after_attempt, wait_fixed

from app.settings import settings


def _client():
    return httpx.AsyncClient(timeout=settings.HTTP_TIMEOUT_SECONDS)


class PaymentsAdapter:
    def __init__(self):
        self.base = settings.PAYMENTS_SERVICE_URL
    
    async def charge(
        self, rental_id: str, amount: float, metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        url = f"{self.base}/payments/charge"
        payload = {
            "rental_id": rental_id,
            "amount": amount,
            "metadata": metadata,
        }
        async with _client() as c:
            r = await c.post(url, json=payload)
            r.raise_for_status()
            return r.json()