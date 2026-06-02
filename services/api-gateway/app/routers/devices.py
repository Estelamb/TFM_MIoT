from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.auth.jwt import verify_token
from app.stubs import get_stub
from shared.proto_gen import device_pb2

router = APIRouter(prefix="/api/devices", tags=["devices"])

class DeviceCreate(BaseModel):
    name: str; hardware_type: str; description: str = ""

@router.post("", status_code=201)
async def create_device(body: DeviceCreate, _=Depends(verify_token)):
    stub = get_stub("device")
    r = await stub.CreateDevice(device_pb2.CreateDeviceRequest(
        name=body.name, hardware_type=body.hardware_type, description=body.description))
    return {"id": r.id, "name": r.name, "hardware_type": r.hardware_type,
            "description": r.description, "status": r.status, "created_at": r.created_at}

@router.get("")
async def list_devices(_=Depends(verify_token)):
    stub = get_stub("device")
    r = await stub.ListDevices(device_pb2.ListDevicesRequest())
    return [{"id": d.id, "name": d.name, "hardware_type": d.hardware_type,
             "status": d.status, "last_seen_at": d.last_seen_at, "created_at": d.created_at}
            for d in r.devices]

@router.get("/{device_id}")
async def get_device(device_id: str, _=Depends(verify_token)):
    stub = get_stub("device")
    r = await stub.GetDevice(device_pb2.GetDeviceRequest(id=device_id))
    return {"id": r.id, "name": r.name, "hardware_type": r.hardware_type,
            "description": r.description, "status": r.status, "created_at": r.created_at}

@router.delete("/{device_id}", status_code=204)
async def delete_device(device_id: str, _=Depends(verify_token)):
    await get_stub("device").DeleteDevice(device_pb2.DeleteDeviceRequest(id=device_id))
