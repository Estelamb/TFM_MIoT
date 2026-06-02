"""
Escucha telemetría e inferencia desde los dispositivos edge.

Tópicos:
  device/{device_id}/telemetry  →  { cpu_percent, ram_percent, ram_used_mb,
                                      active_model_id, active_script_id, active_deployment_id }
  device/{device_id}/inference  →  { deployment_id, result_json }
"""
import asyncio, json, logging
import aiomqtt
from prometheus_client import Gauge
from app.repositories.monitoring import MonitoringRepository

logger = logging.getLogger(__name__)

# Prometheus gauges (labels: device_id)
CPU_GAUGE = Gauge("aura_device_cpu_percent",    "CPU usage %",    ["device_id"])
RAM_GAUGE = Gauge("aura_device_ram_percent",    "RAM usage %",    ["device_id"])
RAM_MB_GAUGE = Gauge("aura_device_ram_used_mb", "RAM used MB",    ["device_id"])

class MonitoringMQTTListener:
    def __init__(self, mqtt_host: str, mqtt_port: int, repo_factory):
        self._host = mqtt_host
        self._port = mqtt_port
        self._repo_factory = repo_factory  # callable → MonitoringRepository

    async def start(self):
        logger.info("MonitoringMQTTListener starting")
        while True:
            try:
                async with aiomqtt.Client(hostname=self._host, port=self._port) as client:
                    await client.subscribe("device/+/telemetry")
                    await client.subscribe("device/+/inference")
                    async for msg in client.messages:
                        await self._handle(msg)
            except aiomqtt.MqttError as e:
                logger.warning(f"MQTT error: {e} — retrying in 5s")
                await asyncio.sleep(5)

    async def _handle(self, msg):
        try:
            payload = json.loads(msg.payload)
            topic = str(msg.topic)
            parts = topic.split("/")
            device_id = parts[1]

            repo = self._repo_factory()

            if topic.endswith("/telemetry"):
                await repo.upsert_device_state(device_id, {
                    "status": "online",
                    "cpu_percent": payload.get("cpu_percent", 0),
                    "ram_percent": payload.get("ram_percent", 0),
                    "ram_used_mb": payload.get("ram_used_mb", 0),
                    "active_model_id": payload.get("active_model_id", ""),
                    "active_script_id": payload.get("active_script_id", ""),
                    "active_deployment_id": payload.get("active_deployment_id", ""),
                })
                # Update Prometheus metrics
                CPU_GAUGE.labels(device_id=device_id).set(payload.get("cpu_percent", 0))
                RAM_GAUGE.labels(device_id=device_id).set(payload.get("ram_percent", 0))
                RAM_MB_GAUGE.labels(device_id=device_id).set(payload.get("ram_used_mb", 0))

            elif topic.endswith("/inference"):
                await repo.insert_inference_result(
                    device_id,
                    payload.get("deployment_id", ""),
                    payload.get("result_json", "{}"),
                )
        except Exception as e:
            logger.warning(f"Error handling MQTT message: {e}")
