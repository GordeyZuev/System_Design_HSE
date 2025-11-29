"""Configuration settings for User Service."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Application
    app_name: str = "user-service"
    app_version: str = "1.0.0"
    app_host: str = "0.0.0.0"
    app_port: int = 8081
    log_level: str = "INFO"

    # JWT
    jwt_secret: str = "your-secret-key-change-in-production"
    jwt_access_token_expires_minutes: int = 15
    jwt_refresh_token_expires_days: int = 7

    # Cache
    user_cache_ttl: int = 60  # seconds

    # Monitoring
    enable_metrics: bool = True
    metrics_port: int = 9090


settings = Settings()

