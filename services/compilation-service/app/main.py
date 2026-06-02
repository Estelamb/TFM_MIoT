"""Compilation Service entry point.

Starts an async gRPC server on port 50054 that exposes
:class:`~app.grpc_handlers.compilation_handler.CompilationServiceHandler`.
Compilation jobs run as background asyncio tasks so the RPC returns immediately.
"""
import asyncio, sys
sys.path.insert(0, "/app")
from app.config import get_settings
from app.grpc_handlers.compilation_handler import CompilationServiceHandler
from shared.proto_gen import compilation_pb2_grpc
from shared.utils.grpc_server import serve
from shared.utils.logging import configure_logging

async def main():
    s = get_settings()
    configure_logging("compilation-service", s.log_level)
    await serve(
        port=s.grpc_port,
        add_servicer_fn=compilation_pb2_grpc.add_CompilationServiceServicer_to_server,
        servicer_instance=CompilationServiceHandler(s.ai_service_grpc),
        service_names=["aura.compilation.v1.CompilationService"],
    )

if __name__ == "__main__":
    asyncio.run(main())
