"""Deployment Service entry point.

Starts an async gRPC server on port 50055 and an MQTT event listener
in a background task. The listener updates deployment status in
PostgreSQL when edge devices publish ``deploy_ack`` or ``deploy_failed``.
"""
import asyncio, sys
sys.path.insert(0, "/app")
from app.config import get_settings
from app.grpc_handlers.deployment_handler import DeploymentServiceHandler
from app.mqtt.listener import DeploymentEventListener
from app.models.orm import Base
from shared.proto_gen import deployment_pb2_grpc
from shared.utils.database import build_engine, build_session_factory
from shared.utils.grpc_server import serve
from shared.utils.logging import configure_logging
from shared.utils.minio import init_minio, ensure_buckets

async def main():
    s = get_settings()
    configure_logging("deployment-service", s.log_level)
    engine = build_engine(s.postgres_dsn)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sf = build_session_factory(engine)
    init_minio(s.minio_endpoint, s.minio_access_key, s.minio_secret_key, s.minio_secure,
               {"compiled": s.minio_bucket_compiled, "scripts": s.minio_bucket_scripts})
    await ensure_buckets()

    listener = DeploymentEventListener(s.mqtt_host, s.mqtt_port, sf)
    asyncio.create_task(listener.start())

    await serve(
        port=s.grpc_port,
        add_servicer_fn=deployment_pb2_grpc.add_DeploymentServiceServicer_to_server,
        servicer_instance=DeploymentServiceHandler(sf, s.mqtt_host, s.mqtt_port),
        service_names=["aura.deployment.v1.DeploymentService"],
    )

if __name__ == "__main__":
    asyncio.run(main())
