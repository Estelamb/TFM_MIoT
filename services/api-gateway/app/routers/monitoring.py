from fastapi import APIRouter, Depends, Query
from app.auth.jwt import verify_token
from app.stubs import get_stub
from shared.proto_gen import monitoring_pb2

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])

@router.get("/devices")
async def list_device_states(_=Depends(verify_token)):
    r = await get_stub("monitoring").ListDeviceStates(monitoring_pb2.ListDeviceStatesRequest())
    return [{"device_id": s.device_id, "status": s.status, "cpu_percent": s.cpu_percent,
             "ram_percent": s.ram_percent, "ram_used_mb": s.ram_used_mb,
             "active_model_id": s.active_model_id, "active_deployment_id": s.active_deployment_id,
             "last_seen_at": s.last_seen_at, "coordinates": list(s.coordinates)} for s in r.states]

@router.get("/devices/{device_id}")
async def get_device_state(device_id: str, _=Depends(verify_token)):
    s = await get_stub("monitoring").GetDeviceState(
        monitoring_pb2.GetDeviceStateRequest(device_id=device_id))
    return {"device_id": s.device_id, "status": s.status, "cpu_percent": s.cpu_percent,
            "ram_percent": s.ram_percent, "ram_used_mb": s.ram_used_mb,
            "active_model_id": s.active_model_id, "active_script_id": s.active_script_id,
            "active_deployment_id": s.active_deployment_id, "last_seen_at": s.last_seen_at,
            "coordinates": list(s.coordinates)}

@router.get("/devices/{device_id}/inference")
async def get_inference_results(device_id: str, limit: int = Query(20, ge=1, le=100),
                                 _=Depends(verify_token)):
    r = await get_stub("monitoring").GetInferenceResults(
        monitoring_pb2.GetInferenceResultsRequest(device_id=device_id, limit=limit))
    return [{"timestamp": i.timestamp, "deployment_id": i.deployment_id,
             "result_json": i.result_json} for i in r.results]
