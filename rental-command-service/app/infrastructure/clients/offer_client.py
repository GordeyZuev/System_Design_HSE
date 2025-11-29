from typing import Any, Dict
import httpx
from tenacity import retry, stop_after_attempt, wait_fixed
from app.settings import settings


def _client():
    return httpx.AsyncClient(timeout=settings.HTTP_TIMEOUT_SECONDS)


class OfferClient:
    def __init__(self, cfg_client):
        self.cfg = cfg_client

    async def validate_offer(self, offer_id: str, user_id: str) -> Dict[str, Any]:
        cfg = await self.cfg.get_config()
        base = cfg["offer_service_url"].rstrip("/")
        url = f"{base}/{offer_id}/validate"

        async with _client() as c:
            r = await c.post(url, params={"user_id": user_id})
            r.raise_for_status()
            return r.json()