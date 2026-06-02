"""Monitoring Service entry point.

Starts an async gRPC server on port 50056, a Prometheus HTTP server
on port 9100, and an MQTT listener that writes device telemetry and
inference results to MongoDB.
"""
import asyncio, sys, threading
sys.path.insert(0, "/app")
from motor.motor_asyncio import AsyncIOMotorClient
from prometheus_client import start_http_server
from app.config import get_settings
from app.grpc_handlers.monitoring_handler import MonitoringServiceHandler
from app.mqtt.listener import MonitoringMQTTListener
from app.repositories.monitoring import MonitoringRepository
from shared.proto_gen import monitoring_pb2_grpc
from shared.utils.grpc_server import serve
from shared.utils.logging import configure_logging

async def main():
    s = get_settings()
    configure_logging("monitoring-service", s.log_level)

    mongo = AsyncIOMotorClient(s.mongo_uri)
    db = mongo[s.mongo_db]

    def repo_factory(): return MonitoringRepository(db)

    start_http_server(s.prometheus_port)

    listener = MonitoringMQTTListener(s.mqtt_host, s.mqtt_port, repo_factory)
    asyncio.create_task(listener.start())

    await serve(
        port=s.grpc_port,
        add_servicer_fn=monitoring_pb2_grpc.add_MonitoringServiceServicer_to_server,
        servicer_instance=MonitoringServiceHandler(repo_factory),
        service_names=["aura.monitoring.v1.MonitoringService"],
    )

if __name__ == "__main__":
    asyncio.run(main())
