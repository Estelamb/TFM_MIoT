from functools import lru_cache
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    postgres_dsn: str = "postgresql+asyncpg://aura:aura_dev@localhost:5432/aura"
    grpc_port: int = 50051
    log_level: str = "DEBUG"
    class Config: env_file = ".env"

@lru_cache
def get_settings(): return Settings()
