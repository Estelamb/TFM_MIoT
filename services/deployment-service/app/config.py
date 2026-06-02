from functools import lru_cache
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    postgres_dsn: str = "postgresql+asyncpg://aura:aura_dev@localhost:5432/aura"
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "aura"
    minio_secret_key: str = "aura_dev"
    minio_secure: bool = False
    minio_bucket_compiled: str = "compiled"
    minio_bucket_scripts: str = "scripts"
    mqtt_host: str = "localhost"
    mqtt_port: int = 1883
    ai_service_grpc: str = "ai-service:50052"
    script_service_grpc: str = "script-service:50053"
    download_url_expiry_seconds: int = 3600
    grpc_port: int = 50055
    log_level: str = "DEBUG"
    class Config: env_file = ".env"

@lru_cache
def get_settings(): return Settings()
