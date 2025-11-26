"""Tariff Service client with LRU cache."""
import logging
import time
from typing import Dict, Optional, Tuple

from cachetools import TTLCache

from app.config import settings
from app.domain.exceptions import TariffNotFoundException, TariffServiceUnavailableException
from app.domain.models import TariffInfo, UserSegment
from app.infrastructure.clients.base import BaseHTTPClient

logger = logging.getLogger(__name__)


class TariffClient:
    """Client for Tariff Service with LRU+TTL cache."""

    def __init__(
        self,
        base_url: str = settings.tariff_service_url,
        timeout: float = settings.tariff_service_timeout,
        cache_ttl: int = settings.tariff_cache_ttl,
        cache_max_size: int = settings.tariff_cache_max_size,
    ):
        self.http_client = BaseHTTPClient(base_url, timeout)
        # LRU cache with TTL
        self.cache: TTLCache = TTLCache(maxsize=cache_max_size, ttl=cache_ttl)

    async def close(self) -> None:
        """Close the client."""
        await self.http_client.close()

    def _make_cache_key(
        self, station_id: str, segment: Optional[UserSegment] = None
    ) -> str:
        """Make cache key."""
        return f"{station_id}:{segment.value if segment else 'STANDARD'}"

    async def get_tariff(
        self, station_id: str, segment: Optional[UserSegment] = None
    ) -> TariffInfo:
        """Get tariff information with caching.

        При протухании TTL возвращает ошибку (использование устаревших тарифов запрещено).
        """
        cache_key = self._make_cache_key(station_id, segment)

        # Check cache
        if cache_key in self.cache:
            logger.debug(f"Returning cached tariff for {cache_key}")
            return self.cache[cache_key]

        # Fetch from service
        try:
            logger.info(f"Fetching tariff from Tariff Service: {cache_key}")
            response = await self.http_client.get(
                "/api/v1/tariffs",
                params={
                    "station_id": station_id,
                    "segment": segment.value if segment else "STANDARD",
                },
            )

            if not response or "tariff_id" not in response:
                raise TariffNotFoundException(station_id)

            tariff = TariffInfo(**response)

            # Store in cache
            self.cache[cache_key] = tariff

            return tariff
        except TariffNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Failed to fetch tariff for {cache_key}: {e}")
            raise TariffServiceUnavailableException()

    async def get_greedy_tariff(self, station_id: str) -> TariffInfo:
        """Get greedy (maximum rate) tariff for fallback pricing."""
        try:
            logger.info(f"Fetching greedy tariff for station {station_id}")
            response = await self.http_client.get(
                "/api/v1/tariffs/greedy",
                params={"station_id": station_id},
            )

            if not response or "tariff_id" not in response:
                # Fallback: create synthetic greedy tariff
                logger.warning("Creating synthetic greedy tariff")
                return TariffInfo(
                    tariff_id=f"greedy-{station_id}",
                    station_id=station_id,
                    base_rate=10.0 * settings.greedy_pricing_multiplier,
                    segment_multiplier=settings.greedy_pricing_multiplier,
                    currency="RUB",
                    version="greedy-v1",
                    rules={"type": "greedy"},
                )

            return TariffInfo(**response)
        except Exception as e:
            logger.error(f"Failed to fetch greedy tariff: {e}")
            # Return synthetic greedy tariff
            return TariffInfo(
                tariff_id=f"greedy-{station_id}",
                station_id=station_id,
                base_rate=10.0 * settings.greedy_pricing_multiplier,
                segment_multiplier=settings.greedy_pricing_multiplier,
                currency="RUB",
                version="greedy-v1",
                rules={"type": "greedy"},
            )

    def clear_cache(self) -> None:
        """Clear the cache."""
        self.cache.clear()

