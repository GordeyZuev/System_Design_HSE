"""External service clients."""
from app.infrastructure.clients.config_client import ConfigClient
from app.infrastructure.clients.tariff_client import TariffClient
from app.infrastructure.clients.user_client import UserClient

__all__ = ["ConfigClient", "TariffClient", "UserClient"]

