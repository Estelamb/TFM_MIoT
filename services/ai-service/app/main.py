"""AI Service entry point.

Starts an async gRPC server on port 50052 that exposes
:class:`~app.grpc_handlers.ai_handler.AIServiceHandler`.
Manages model metadata in PostgreSQL and artefacts in MinIO.
"""
import asyncio, sys
sys.path.insert(0, "/app")
from app.config import get_settings
from app.grpc_handlers.ai_handler import AIServiceHandler
from app.models.orm import Base
from shared.proto_gen import ai_pb2_grpc
from shared.utils.database import build_engine, build_session_factory
from shared.utils.grpc_server import serve
from shared.utils.logging import configure_logging
from shared.utils.minio import init_minio, ensure_buckets

async def main():
    s = get_settings()
    configure_logging("ai-service", s.log_level)
    engine = build_engine(s.postgres_dsn)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sf = build_session_factory(engine)
    init_minio(s.minio_endpoint, s.minio_access_key, s.minio_secret_key, s.minio_secure,
               {
                   "models": s.minio_bucket_models,
                   "compiled": s.minio_bucket_compiled,
                   "datasets": s.minio_bucket_datasets,
               })
    await ensure_buckets()
    await serve(
        port=s.grpc_port,
        add_servicer_fn=ai_pb2_grpc.add_AIServiceServicer_to_server,
        servicer_instance=AIServiceHandler(sf),
        service_names=["aura.ai.v1.AIService"],
    )

if __name__ == "__main__":
    asyncio.run(main())
