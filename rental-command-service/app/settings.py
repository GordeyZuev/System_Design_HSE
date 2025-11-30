from typing import Optional

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):

    SERVICE_PORT: int = 8003
    
    OFFER_SERVICE_URL: str = "http://localhost:8002"
    STATIONS_SERVICE_URL: str = "http://localhost:8005"
    PAYMENTS_SERVICE_URL: str = "http://localhost:8006"
    SERVICE_PORT: int = Field(8003, env="SERVER_PORT")

    OUTBOX_POLL_INTERVAL_SECONDS: int = 5
    HTTP_TIMEOUT_SECONDS: int = 5
    STATIONS_RETRY: int = 3
    PAYMENTS_RETRY: int = 3
    DB_URL: Optional[str] = "postgresql+asyncpg://postgres@localhost:5432/rental_cmd_shard_0"
    
    log_level: str = "INFO"
    app_name: str = "rental-command-service"
    app_version: str = "1.0.0"
    app_host: str = "0.0.0.0"
    app_port: int = 8003

    model_config = {"env_file": ".env", "extra": "ignore"}

settings = Settings()
