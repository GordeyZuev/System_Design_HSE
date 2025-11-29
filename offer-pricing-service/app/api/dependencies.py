"""API dependencies with dependency injection."""
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.clients import ConfigClient, TariffClient, UserClient
from app.infrastructure.database import get_async_session
from app.infrastructure.repositories import OfferRepository
from app.infrastructure.repositories_postgres import PostgresOfferRepository
from app.services.offer_service import OfferService

# Singleton instances for clients
_tariff_client: Optional[TariffClient] = None
_user_client: Optional[UserClient] = None
_config_client: Optional[ConfigClient] = None


def get_tariff_client() -> TariffClient:
    """Get TariffClient singleton."""
    global _tariff_client
    if _tariff_client is None:
        _tariff_client = TariffClient()
    return _tariff_client


def get_user_client() -> UserClient:
    """Get UserClient singleton."""
    global _user_client
    if _user_client is None:
        _user_client = UserClient()
    return _user_client


def get_config_client() -> ConfigClient:
    """Get ConfigClient singleton."""
    global _config_client
    if _config_client is None:
        _config_client = ConfigClient()
    return _config_client


async def get_offer_repository(
    session: AsyncSession = None,
) -> AsyncGenerator[OfferRepository, None]:
    """Get PostgreSQL OfferRepository with dependency injection."""
    if session is None:
        async for db_session in get_async_session():
            yield PostgresOfferRepository(db_session)
    else:
        yield PostgresOfferRepository(session)


async def get_offer_service() -> AsyncGenerator[OfferService, None]:
    """Get OfferService with dependencies."""
    async for repo in get_offer_repository():
        yield OfferService(
            offer_repository=repo,
            tariff_client=get_tariff_client(),
            user_client=get_user_client(),
            config_client=get_config_client(),
        )
