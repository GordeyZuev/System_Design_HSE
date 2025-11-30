from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    '''
    #SERVICE_PORT: int = 8003
    SERVICE_PORT=os.getenv("SERVICE_PORT", 8003)
    POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")

    # External Services
    OFFER_SERVICE_URL: str = os.getenv("OFFER_SERVICE_URL", "http://offer-service:8002")
    STATIONS_SERVICE_URL: str = os.getenv("STATIONS_SERVICE_URL", "http://stations-adapter:8005")
    PAYMENTS_SERVICE_URL: str = os.getenv("PAYMENTS_SERVICE_URL", "http://payments-adapter:8006")
    
    OFFER_SERVICE_URL = "http://offer-service:8002"
    STATIONS_SERVICE_URL = "http://stations-adapter:8005"
    PAYMENTS_SERVICE_URL = "http://payments-adapter:8006"
    
    OUTBOX_POLL_INTERVAL_SECONDS: int = 5
    HTTP_TIMEOUT_SECONDS: int = 5
    STATIONS_RETRY: int = 3
    PAYMENTS_RETRY: int = 3

    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "password"

    DB_URL_SHARD_0: str = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@rental-db-shard0-master:5432/rental_cmd_test"
    DB_URL_SHARD_0_REPLICA: str = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@rental-cmd-db-replica:5432/rental_cmd_test"

    DB_URL_SHARD_1: str = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@rental-db-shard1-master:5432/rental_cmd_test"
    DB_URL_SHARD_1_REPLICA: str = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@rental-db-replica2:5432/rental_cmd_test"


    
    
    model_config = {"extra": "ignore"}

    
    CONFIG_SERVICE_URL: str = "http://localhost:8004"
    OFFER_SERVICE_URL: str = "http://localhost:8002"
    STATIONS_SERVICE_URL: str = "http://localhost:8005"
    PAYMENTS_SERVICE_URL: str = "http://localhost:8006"

    "env_file": ".env", 
    '''
    SERVICE_PORT: int = int(os.getenv("SERVER_PORT", 8003))

    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "password")

    # External Services (переопределяются через docker-compose)
    OFFER_SERVICE_URL: str = os.getenv("OFFER_SERVICE_URL", "http://offer-service:8002")
    STATIONS_SERVICE_URL: str = os.getenv("STATIONS_SERVICE_URL", "http://stations-adapter:8005")
    PAYMENTS_SERVICE_URL: str = os.getenv("PAYMENTS_SERVICE_URL", "http://payments-adapter:8006")

    OUTBOX_POLL_INTERVAL_SECONDS: int = 5
    HTTP_TIMEOUT_SECONDS: int = 5
    STATIONS_RETRY: int = 3
    PAYMENTS_RETRY: int = 3

    
    DB_URL_SHARD_0: str = (
        f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
        f"@{os.getenv('DB_MASTER_HOST', 'rental-db-shard0-master')}:5432/rental_cmd_test"
    )

    DB_URL_SHARD_0_REPLICA: str = (
        f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
        f"@{os.getenv('DB_REPLICA_HOST', 'rental-cmd-db-replica')}:5432/rental_cmd_test"
    )

    DB_URL_SHARD_1: str = (
        f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
        "@rental-db-shard1-master:5432/rental_cmd_test"
    )

    DB_URL_SHARD_1_REPLICA: str = (
        f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
        "@rental-db-replica2:5432/rental_cmd_test"
    )

    model_config = {
        "extra": "ignore"
    }




settings = Settings()
