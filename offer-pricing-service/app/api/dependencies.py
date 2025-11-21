"""API dependencies with in-memory storage."""
from typing import Optional

from app.infrastructure.clients import ConfigClient, TariffClient, UserClient
from app.infrastructure.repositories_inmemory import InMemoryOfferRepository, OfferRepository
from app.services.offer_service import OfferService

# Singleton instances
_tariff_client: Optional[TariffClient] = None
_user_client: Optional[UserClient] = None
_config_client: Optional[ConfigClient] = None
_offer_repository: Optional[InMemoryOfferRepository] = None


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


def get_offer_repository() -> OfferRepository:
    """Get in-memory OfferRepository singleton."""
    global _offer_repository
    if _offer_repository is None:
        _offer_repository = InMemoryOfferRepository()
    return _offer_repository


def get_offer_service() -> OfferService:
    """Get OfferService with dependencies."""
    return OfferService(
        offer_repository=get_offer_repository(),
        tariff_client=get_tariff_client(),
        user_client=get_user_client(),
        config_client=get_config_client(),
    )

