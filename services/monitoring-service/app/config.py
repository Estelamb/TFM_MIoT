from functools import lru_cache
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    mongo_uri: str = "mongodb://aura:aura_dev@localhost:27017/aura?authSource=admin"
    mongo_db: str = "aura"
    mqtt_host: str = "localhost"
    mqtt_port: int = 1883
    prometheus_port: int = 9100
    grpc_port: int = 50056
    log_level: str = "DEBUG"
    class Config: env_file = ".env"

@lru_cache
def get_settings(): return Settings()
