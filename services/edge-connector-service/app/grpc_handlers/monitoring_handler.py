import grpc
from app.repositories.monitoring import MonitoringRepository
from shared.proto_gen import monitoring_pb2, monitoring_pb2_grpc

def _state_to_proto(s: dict) -> monitoring_pb2.DeviceStateResponse:
    res = monitoring_pb2.DeviceStateResponse(
        device_id=s.get("device_id", ""),
        status=s.get("status", "offline"),
        active_model_id=s.get("active_model_id", ""),
        active_script_id=s.get("active_script_id", ""),
        active_deployment_id=s.get("active_deployment_id", ""),
        cpu_percent=float(s.get("cpu_percent", 0.0)),
        ram_percent=float(s.get("ram_percent", 0.0)),
        ram_used_mb=float(s.get("ram_used_mb", 0.0)),
        last_seen_at=s.get("last_seen_at", ""),
        latency_ms=float(s.get("latency_ms", 0.0)),
    )
    if "coordinates" in s and s["coordinates"]:
        res.coordinates.extend(s["coordinates"])
    return res

class MonitoringServiceHandler(monitoring_pb2_grpc.MonitoringServiceServicer):
    def __init__(self, repo_factory): self._repo_factory = repo_factory

    async def GetDeviceState(self, req, ctx):
        repo = self._repo_factory()
        state = await repo.get_device_state(req.device_id)
        if not state:
            await ctx.abort(grpc.StatusCode.NOT_FOUND, "No state for this device"); return
        return _state_to_proto(state)

    async def ListDeviceStates(self, req, ctx):
        repo = self._repo_factory()
        states = await repo.list_device_states()
        return monitoring_pb2.ListDeviceStatesResponse(states=[_state_to_proto(s) for s in states])

    async def GetInferenceResults(self, req, ctx):
        repo = self._repo_factory()
        results = await repo.get_inference_results(req.device_id, req.limit or 20)
        protos = [monitoring_pb2.InferenceResult(
            device_id=r["device_id"], deployment_id=r.get("deployment_id", ""),
            timestamp=r["timestamp"], result_json=r["result_json"],
        ) for r in results]
        return monitoring_pb2.GetInferenceResultsResponse(results=protos)
