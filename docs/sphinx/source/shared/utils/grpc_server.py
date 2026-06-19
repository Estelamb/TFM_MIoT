"""
gRPC server helper for AURA services.

Provides a single :func:`serve` coroutine that wires up an asyncio gRPC
server with server reflection enabled, making it compatible with tools
such as ``grpcurl`` and Postman.
"""
import asyncio
import logging
import grpc
from grpc_reflection.v1alpha import reflection

logger = logging.getLogger(__name__)


async def serve(
    port: int,
    add_servicer_fn,
    servicer_instance,
    service_names: list[str],
) -> None:
    """Start an async gRPC server with reflection.

    Creates a :class:`grpc.aio.Server`, registers the given servicer,
    enables server reflection, binds to ``[::]:{port}`` and waits for
    termination.

    Args:
        port:              TCP port to listen on.
        add_servicer_fn:   The generated ``add_XxxServicer_to_server``
                           function from the service's ``_pb2_grpc`` module.
        servicer_instance: An instance of the concrete servicer class.
        service_names:     List of fully-qualified service names used for
                           reflection, e.g.
                           ``["aura.device.v1.DeviceService"]``.

    Example:
        >>> await serve(50051, add_DeviceServiceServicer_to_server,
        ...             DeviceServiceHandler(sf), ["aura.device.v1.DeviceService"])
    """
    server = grpc.aio.server()
    add_servicer_fn(servicer_instance, server)
    reflection.enable_server_reflection(
        service_names + [reflection.SERVICE_NAME], server
    )
    server.add_insecure_port(f"[::]:{port}")
    await server.start()
    logger.info(f"gRPC server listening on :{port}")
    await server.wait_for_termination()
