from functools import lru_cache
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    secret_key: str = "dev-insecure-change-me"
    access_token_expire_minutes: int = 60
    # gRPC upstreams
    device_service_grpc: str = "device-service:50051"
    ai_service_grpc: str = "ai-service:50052"
    script_service_grpc: str = "script-service:50053"
    compilation_service_grpc: str = "mlops-service:50052"
    deployment_service_grpc: str = "edge-connector-service:50053"
    monitoring_service_grpc: str = "edge-connector-service:50053"
    # MinIO (el gateway sube ficheros directamente)
    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "aura"
    minio_secret_key: str = "aura_dev"
    minio_secure: bool = False
    minio_bucket_models: str = "models"
    minio_bucket_compiled: str = "compiled"
    minio_bucket_scripts: str = "scripts"
    minio_bucket_datasets: str = "datasets"
    minio_bucket_base_models: str = "base-models"
    log_level: str = "DEBUG"
    redis_url: str = "redis://localhost:6379"

    class Config:
        env_file = ".env"

@lru_cache
def get_settings():
    return Settings()
