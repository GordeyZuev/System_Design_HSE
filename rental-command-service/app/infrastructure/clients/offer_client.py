from typing import Any, Dict

import httpx
from tenacity import retry, stop_after_attempt, wait_fixed

from app.settings import settings


def _client():
    return httpx.AsyncClient(timeout=settings.HTTP_TIMEOUT_SECONDS)


class OfferClient:
    def __init__(self):
        self.base = settings.OFFER_SERVICE_URL
    
    async def validate_offer(
        self, offer_id: str, user_id: str
    ) -> Dict[str, Any]:
        url = f"{self.base}/internal/offers/{offer_id}/validate"

        async with _client() as c:
            try:
                r = await c.post(url, params={"user_id": user_id})
                r.raise_for_status()
                return r.json()
            except httpx.HTTPStatusError as e:
                
                return e.response.json()