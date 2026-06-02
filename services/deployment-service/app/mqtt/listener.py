"""
MQTT event listener for the Deployment Service.

Subscribes to ``device/+/events`` and updates deployment status in
PostgreSQL when an edge agent publishes a ``deploy_ack`` or
``deploy_failed`` event. Telemetry topics are handled by the
monitoring-service instead.
"""
import asyncio, json, logging
import aiomqtt
from sqlalchemy.ext.asyncio import async_sessionmaker
from app.repositories.deployments import DeploymentRepository

logger = logging.getLogger(__name__)

class DeploymentEventListener:
    def __init__(self, mqtt_host: str, mqtt_port: int, sf: async_sessionmaker):
        self._host = mqtt_host; self._port = mqtt_port; self._sf = sf

    async def start(self):
        logger.info("DeploymentEventListener starting")
        while True:
            try:
                async with aiomqtt.Client(hostname=self._host, port=self._port) as client:
                    await client.subscribe("device/+/events")
                    async for msg in client.messages:
                        await self._handle(msg)
            except aiomqtt.MqttError as e:
                logger.warning(f"MQTT error: {e} — retrying in 5s")
                await asyncio.sleep(5)

    async def _handle(self, msg):
        try:
            payload = json.loads(msg.payload)
        except Exception:
            return
        event = payload.get("event")
        dep_id = payload.get("deployment_id")
        if not event or not dep_id:
            return
        async with self._sf() as s:
            repo = DeploymentRepository(s)
            dep = await repo.get(dep_id)
            if not dep:
                logger.warning(f"Unknown deployment_id: {dep_id}"); return
            if event == "deploy_ack":
                await repo.mark_running(dep)
                logger.info(f"Deployment {dep_id} → running")
            elif event == "deploy_failed":
                await repo.mark_failed(dep, payload.get("error", "unknown"))
                logger.warning(f"Deployment {dep_id} → failed")
