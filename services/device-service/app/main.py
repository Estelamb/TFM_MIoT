"""Device Service entry point.

Starts an async gRPC server on port 50051 that exposes
:class:`~app.grpc_handlers.device_handler.DeviceServiceHandler`.
Creates the PostgreSQL schema on first run.
"""
import asyncio, logging, sys
sys.path.insert(0, "/app")
from app.config import get_settings
from app.grpc_handlers.device_handler import DeviceServiceHandler
from app.models.orm import Base
from shared.proto_gen import device_pb2, device_pb2_grpc
from shared.utils.database import build_engine, build_session_factory
from shared.utils.grpc_server import serve
from shared.utils.logging import configure_logging

async def main():
    s = get_settings()
    configure_logging("device-service", s.log_level)
    engine = build_engine(s.postgres_dsn)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sf = build_session_factory(engine)
    await serve(
        port=s.grpc_port,
        add_servicer_fn=device_pb2_grpc.add_DeviceServiceServicer_to_server,
        servicer_instance=DeviceServiceHandler(sf),
        service_names=["aura.device.v1.DeviceService"],
    )

if __name__ == "__main__":
    asyncio.run(main())
