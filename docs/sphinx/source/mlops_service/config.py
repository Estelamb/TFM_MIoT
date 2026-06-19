from functools import lru_cache
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    postgres_dsn: str = "postgresql+asyncpg://aura:aura_dev@localhost:5432/aura"
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "aura"
    minio_secret_key: str = "aura_dev"
    minio_secure: bool = False
    minio_bucket_models: str = "models"
    minio_bucket_compiled: str = "compiled"
    ai_service_grpc: str = "registry-service:50051"
    grpc_port: int = 50052
    docker_socket: str = "unix:///var/run/docker.sock"
    log_level: str = "DEBUG"
    redis_url: str = "redis://localhost:6379"
    class Config: env_file = ".env"

@lru_cache
def get_settings(): return Settings()
