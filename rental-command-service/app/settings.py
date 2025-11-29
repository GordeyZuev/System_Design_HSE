from typing import Optional

from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    SERVICE_PORT: int = 8001
    CONFIG_SERVICE_URL: AnyHttpUrl
    CONFIG_TTL_SECONDS: int = 60
    OUTBOX_POLL_INTERVAL_SECONDS: int = 5
    HTTP_TIMEOUT_SECONDS: int = 5
    STATIONS_RETRY: int = 3
    PAYMENTS_RETRY: int = 3

    DB_URL_SHARD_0: Optional[str] = None
    DB_URL_SHARD_1: Optional[str] = None

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
