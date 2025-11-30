"""Configuration settings for Offer & Pricing Service."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Application
    app_name: str = "offer-pricing-service"
    app_version: str = "1.0.0"
    app_host: str = "0.0.0.0"
    app_port: int = 8002
    log_level: str = "INFO"

    # Database
    database_url: str = "postgresql+asyncpg://postgres:password@offer-db:5432/offer_test"

    # External Services
    
    user_service_url: str = "http://user-service:8001"
    config_service_url: str = "http://config-service:8007"
    tariff_service_url: str = "http://tariff-service:8008"
    
    # Timeouts
    user_service_timeout: float = 2.0
    tariff_service_timeout: float = 3.0
    config_service_timeout: float = 1.0

    # Cache Settings
    tariff_cache_ttl: int = 600  # 10 minutes
    tariff_cache_max_size: int = 1000
    config_cache_ttl: int = 60  # 1 minute

    # Offer Settings
    offer_default_ttl: int = 300  # 5 minutes
    greedy_pricing_multiplier: float = 1.5

    # Monitoring
    enable_metrics: bool = True
    metrics_port: int = 9090


settings = Settings()

