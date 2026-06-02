import json, logging
import grpc
import aiomqtt
from datetime import timedelta
from sqlalchemy.ext.asyncio import async_sessionmaker
from shared.proto_gen import deployment_pb2, deployment_pb2_grpc
from shared.utils.minio import presigned_url
from app.repositories.deployments import DeploymentRepository

logger = logging.getLogger(__name__)

def _to_proto(d) -> deployment_pb2.DeploymentResponse:
    return deployment_pb2.DeploymentResponse(
        id=d.id, device_id=d.device_id, model_id=d.model_id, script_id=d.script_id,
        status=d.status,
        sent_at=d.sent_at.isoformat() if d.sent_at else "",
        running_at=d.running_at.isoformat() if d.running_at else "",
        error_msg=d.error_msg or "",
        created_at=d.created_at.isoformat(),
    )

class DeploymentServiceHandler(deployment_pb2_grpc.DeploymentServiceServicer):
    def __init__(self, sf: async_sessionmaker, mqtt_host: str, mqtt_port: int):
        self._sf = sf
        self._mqtt_host = mqtt_host
        self._mqtt_port = mqtt_port

    async def CreateDeployment(self, req, ctx):
        async with self._sf() as s:
            repo = DeploymentRepository(s)
            device = await repo.get_device(req.device_id)
            if not device:
                await ctx.abort(grpc.StatusCode.NOT_FOUND, "Device not found"); return
            model = await repo.get_model(req.model_id)
            if not model:
                await ctx.abort(grpc.StatusCode.NOT_FOUND, "Model not found"); return
            if model.compile_status != "ready":
                await ctx.abort(grpc.StatusCode.FAILED_PRECONDITION,
                                f"Model not compiled yet (status: {model.compile_status})"); return
            script = await repo.get_script(req.script_id)
            if not script:
                await ctx.abort(grpc.StatusCode.NOT_FOUND, "Script not found"); return

            dep = await repo.create(req.device_id, req.model_id, req.script_id)

            # URLs presignadas para descarga en el edge
            model_url = await presigned_url("compiled", model.compiled_key)
            script_url = await presigned_url("scripts", script.script_key)

            command = {
                "command": "deploy",
                "deployment_id": dep.id,
                "model_url": model_url,
                "model_sha256": model.compiled_sha256,
                "script_url": script_url,
                "script_sha256": script.script_sha256,
            }
            try:
                async with aiomqtt.Client(hostname=self._mqtt_host, port=self._mqtt_port) as client:
                    await client.publish(f"device/{req.device_id}/commands", json.dumps(command))
                await repo.mark_sent(dep)
                logger.info(f"Deploy command sent → device {req.device_id}, deployment {dep.id}")
            except Exception as e:
                await repo.mark_failed(dep, str(e))
                await ctx.abort(grpc.StatusCode.UNAVAILABLE, f"MQTT error: {e}"); return

            await s.refresh(dep)
            return _to_proto(dep)

    async def GetDeployment(self, req, ctx):
        async with self._sf() as s:
            d = await DeploymentRepository(s).get(req.id)
            if not d: await ctx.abort(grpc.StatusCode.NOT_FOUND, "Deployment not found"); return
            return _to_proto(d)

    async def ListDeployments(self, req, ctx):
        async with self._sf() as s:
            deps = await DeploymentRepository(s).list_all()
            return deployment_pb2.ListDeploymentsResponse(deployments=[_to_proto(d) for d in deps])

    async def ListDeviceDeployments(self, req, ctx):
        async with self._sf() as s:
            deps = await DeploymentRepository(s).list_for_device(req.device_id)
            return deployment_pb2.ListDeploymentsResponse(deployments=[_to_proto(d) for d in deps])
