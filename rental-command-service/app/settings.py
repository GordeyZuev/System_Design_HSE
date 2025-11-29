from typing import Optional

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):

    SERVICE_PORT: int = 8003
    
    OFFER_SERVICE_URL: str = "http://localhost:8002"
    STATIONS_SERVICE_URL: str = "http://localhost:8005"
    PAYMENTS_SERVICE_URL: str = "http://localhost:8006"
    SERVICE_PORT: int = Field(8001, env="SERVER_PORT")

    OUTBOX_POLL_INTERVAL_SECONDS: int = 5
    HTTP_TIMEOUT_SECONDS: int = 5
    STATIONS_RETRY: int = 3
    PAYMENTS_RETRY: int = 3
    DB_URL_SHARD_0: Optional[str] = "postgresql+asyncpg://postgres:password@rental-cmd-db-master:5432/rental_cmd"
    DB_URL_SHARD_1: Optional[str] = "postgresql+asyncpg://postgres:password@rental-cmd-db-master:5432/rental_cmd"


    model_config = {"env_file": ".env", "extra": "ignore"}

settings = Settings()
