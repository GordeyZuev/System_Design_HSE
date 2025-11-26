"""Base client class."""
import logging
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


class BaseHTTPClient:
    """Base HTTP client with retry and timeout logic."""

    def __init__(self, base_url: str, timeout: float = 5.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)

    async def close(self) -> None:
        """Close the client."""
        await self.client.aclose()

    async def get(
        self, path: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make GET request."""
        url = f"{self.base_url}{path}"
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException as e:
            logger.error(f"Timeout calling {url}: {e}")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error calling {url}: {e.response.status_code}")
            raise
        except Exception as e:
            logger.error(f"Error calling {url}: {e}")
            raise

    async def post(
        self, path: str, data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make POST request."""
        url = f"{self.base_url}{path}"
        try:
            response = await self.client.post(url, json=data)
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException as e:
            logger.error(f"Timeout calling {url}: {e}")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error calling {url}: {e.response.status_code}")
            raise
        except Exception as e:
            logger.error(f"Error calling {url}: {e}")
            raise

