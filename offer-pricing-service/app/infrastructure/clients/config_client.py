"""Config Service client with TTL cache."""
import logging
import time
from typing import Optional

from app.config import settings
from app.domain.exceptions import ConfigServiceUnavailableException
from app.domain.models import ConfigData
from app.infrastructure.clients.base import BaseHTTPClient

logger = logging.getLogger(__name__)


class ConfigClient:
    """Client for Config Service with auto-refresh cache."""

    def __init__(
        self,
        base_url: str = settings.config_service_url,
        timeout: float = settings.config_service_timeout,
        cache_ttl: int = settings.config_cache_ttl,
    ):
        self.http_client = BaseHTTPClient(base_url, timeout)
        self.cache_ttl = cache_ttl
        self._cached_config: Optional[ConfigData] = None
        self._cache_timestamp: float = 0

    async def close(self) -> None:
        """Close the client."""
        await self.http_client.close()

    async def get_config(self) -> ConfigData:
        """Get configuration with caching."""
        current_time = time.time()

        # Check if cache is valid
        if (
            self._cached_config is not None
            and current_time - self._cache_timestamp < self.cache_ttl
        ):
            logger.debug("Returning cached config")
            return self._cached_config

        # Fetch new config
        try:
            logger.info("Fetching fresh config from Config Service")
            response = await self.http_client.get("/api/v1/config")
            config = ConfigData(**response)

            # Update cache
            self._cached_config = config
            self._cache_timestamp = current_time

            return config
        except Exception as e:
            logger.error(f"Failed to fetch config: {e}")

            # If we have stale cache, return it
            if self._cached_config is not None:
                logger.warning("Using stale config due to service unavailability")
                return self._cached_config

            # No cache available
            raise ConfigServiceUnavailableException()

    def invalidate_cache(self) -> None:
        """Invalidate the cache."""
        self._cached_config = None
        self._cache_timestamp = 0

