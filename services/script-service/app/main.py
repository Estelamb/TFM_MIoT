"""Script Service entry point.

Starts an async gRPC server on port 50053 that exposes
:class:`~app.grpc_handlers.script_handler.ScriptServiceHandler`.
Stores inference scripts in PostgreSQL and MinIO.
"""
import asyncio, sys
sys.path.insert(0, "/app")
from app.config import get_settings
from app.grpc_handlers.script_handler import ScriptServiceHandler
from app.models.orm import Base
from shared.proto_gen import script_pb2_grpc
from shared.utils.database import build_engine, build_session_factory
from shared.utils.grpc_server import serve
from shared.utils.logging import configure_logging
from shared.utils.minio import init_minio, ensure_buckets

async def main():
    s = get_settings()
    configure_logging("script-service", s.log_level)
    engine = build_engine(s.postgres_dsn)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sf = build_session_factory(engine)
    init_minio(s.minio_endpoint, s.minio_access_key, s.minio_secret_key, s.minio_secure,
               {"scripts": s.minio_bucket_scripts})
    await ensure_buckets()
    await serve(
        port=s.grpc_port,
        add_servicer_fn=script_pb2_grpc.add_ScriptServiceServicer_to_server,
        servicer_instance=ScriptServiceHandler(sf),
        service_names=["aura.script.v1.ScriptService"],
    )

if __name__ == "__main__":
    asyncio.run(main())
