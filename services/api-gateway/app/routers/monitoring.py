from fastapi import APIRouter, Depends, Query, HTTPException
from app.auth.jwt import verify_token
from app.stubs import get_stub
from shared.proto_gen import monitoring_pb2, device_pb2

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])

@router.get("/devices")
async def list_device_states(_=Depends(verify_token)):
    # 1. Fetch valid registered device IDs from registry service
    try:
        devs_res = await get_stub("device").ListDevices(device_pb2.ListDevicesRequest())
        valid_ids = {d.id for d in devs_res.devices}
    except Exception:
        # Fall back to empty filter if registry is down, but log warning
        import logging
        logging.getLogger("api-gateway").warning("Failed to fetch registered devices for filtering telemetry states.")
        valid_ids = None

    r = await get_stub("monitoring").ListDeviceStates(monitoring_pb2.ListDeviceStatesRequest())
    
    # 2. Filter states if we have valid_ids
    states = r.states
    if valid_ids is not None:
        states = [s for s in states if s.device_id in valid_ids]

    return [{"device_id": s.device_id, "status": s.status, "cpu_percent": s.cpu_percent,
             "ram_percent": s.ram_percent, "ram_used_mb": s.ram_used_mb, "latency_ms": s.latency_ms,
             "active_model_id": s.active_model_id, "active_script_id": s.active_script_id, "active_deployment_id": s.active_deployment_id,
             "last_seen_at": s.last_seen_at, "coordinates": list(s.coordinates)} for s in states]

@router.get("/devices/{device_id}")
async def get_device_state(device_id: str, _=Depends(verify_token)):
    # 1. Verify device exists in registry service first
    try:
        await get_stub("device").GetDevice(device_pb2.GetDeviceRequest(id=device_id))
    except Exception:
        raise HTTPException(status_code=404, detail="Device not found in registry")

    s = await get_stub("monitoring").GetDeviceState(
        monitoring_pb2.GetDeviceStateRequest(device_id=device_id))
    return {"device_id": s.device_id, "status": s.status, "cpu_percent": s.cpu_percent,
            "ram_percent": s.ram_percent, "ram_used_mb": s.ram_used_mb, "latency_ms": s.latency_ms,
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
