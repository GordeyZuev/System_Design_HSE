from typing import Optional

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    STATIONS_SERVICE_URL: AnyHttpUrl
    PAYMENTS_SERVICE_URL: AnyHttpUrl
    OFFER_SERVICE_URL: AnyHttpUrl
    SERVICE_PORT: int = Field(8003, env="SERVER_PORT")
    OUTBOX_POLL_INTERVAL_SECONDS: int = 5
    HTTP_TIMEOUT_SECONDS: int = 5
    STATIONS_RETRY: int = 3
    PAYMENTS_RETRY: int = 3
    DB_URL_SHARD_0: Optional[str] = "postgresql+asyncpg://rental-cmd-db-master/rental_cmd_shard_0"
    DB_URL_SHARD_1: Optional[str] = "postgresql+asyncpg://rental-cmd-db-master/rental_cmd_shard_1"

    model_config = {"env_file": ".env", "extra": "ignore"}

settings = Settings()
