from fastapi import APIRouter, Depends
from pydantic import BaseModel
import redis.asyncio as aioredis
from app.auth.jwt import verify_token
from app.stubs import get_stub
from shared.proto_gen import deployment_pb2

router = APIRouter(prefix="/api/deployments", tags=["deployments"])

class DeployRequest(BaseModel):
    device_id: str; model_id: str; script_id: str

@router.post("", status_code=201)
async def create_deployment(body: DeployRequest, _=Depends(verify_token)):
    d = await get_stub("deployment").CreateDeployment(
        deployment_pb2.CreateDeploymentRequest(
            device_id=body.device_id, model_id=body.model_id, script_id=body.script_id))
    return {"id": d.id, "status": d.status, "sent_at": d.sent_at, "created_at": d.created_at}

@router.get("")
async def list_deployments(_=Depends(verify_token)):
    r = await get_stub("deployment").ListDeployments(deployment_pb2.ListDeploymentsRequest())
    return [{"id": d.id, "device_id": d.device_id, "model_id": d.model_id,
             "script_id": d.script_id, "status": d.status, "created_at": d.created_at}
            for d in r.deployments]

@router.get("/device/{device_id}")
async def list_device_deployments(device_id: str, _=Depends(verify_token)):
    r = await get_stub("deployment").ListDeviceDeployments(
        deployment_pb2.ListDeviceDeploymentsRequest(device_id=device_id))
    return [{"id": d.id, "model_id": d.model_id, "script_id": d.script_id,
             "status": d.status, "running_at": d.running_at, "created_at": d.created_at}
            for d in r.deployments]

@router.get("/{deployment_id}")
async def get_deployment(deployment_id: str, _=Depends(verify_token)):
    d = await get_stub("deployment").GetDeployment(
        deployment_pb2.GetDeploymentRequest(id=deployment_id))
    return {"id": d.id, "device_id": d.device_id, "model_id": d.model_id,
            "script_id": d.script_id, "status": d.status, "error_msg": d.error_msg,
            "sent_at": d.sent_at, "running_at": d.running_at, "created_at": d.created_at}


@router.delete("/{deployment_id}", status_code=204)
async def delete_deployment(deployment_id: str, _=Depends(verify_token)):
    from app.config import get_settings
    s_settings = get_settings()
    try:
        redis_client = aioredis.from_url(s_settings.redis_url)
        await redis_client.set(f"cancel:deploy:{deployment_id}", "1", ex=300)
        await redis_client.close()
    except Exception:
        pass
