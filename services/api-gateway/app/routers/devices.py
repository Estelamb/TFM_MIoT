from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.auth.jwt import verify_token
from app.stubs import get_stub
from shared.proto_gen import device_pb2

router = APIRouter(prefix="/api/devices", tags=["devices"])

class DeviceCreate(BaseModel):
    name: str; hardware_type: str; description: str = ""
    sensors: list[str] = []
    actuators: list[str] = []
    others: list[str] = []

class DeviceUpdate(BaseModel):
    name: str
    description: str = ""

@router.post("", status_code=201)
async def create_device(body: DeviceCreate, _=Depends(verify_token)):
    stub = get_stub("device")
    r = await stub.CreateDevice(device_pb2.CreateDeviceRequest(
        name=body.name, hardware_type=body.hardware_type, description=body.description,
        sensors=body.sensors, actuators=body.actuators, others=body.others))
    return {"id": r.id, "name": r.name, "hardware_type": r.hardware_type,
            "description": r.description, "status": r.status, "created_at": r.created_at,
            "sensors": list(r.sensors), "actuators": list(r.actuators), "others": list(r.others)}

@router.get("")
async def list_devices(_=Depends(verify_token)):
    stub = get_stub("device")
    r = await stub.ListDevices(device_pb2.ListDevicesRequest())
    return [{"id": d.id, "name": d.name, "hardware_type": d.hardware_type,
             "status": d.status, "last_seen_at": d.last_seen_at, "created_at": d.created_at,
             "sensors": list(d.sensors), "actuators": list(d.actuators), "others": list(d.others)}
            for d in r.devices]


@router.get("/hardware-types")
async def get_hardware_types(_=Depends(verify_token)):
    from shared.proto_gen import compilation_pb2
    stub = get_stub("compilation")
    r = await stub.GetSupportedHardware(compilation_pb2.GetSupportedHardwareRequest())
    return list(r.hardware_types)


@router.get("/sensors")
async def get_sensors(_=Depends(verify_token)):
    from shared.proto_gen import compilation_pb2
    stub = get_stub("compilation")
    r = await stub.GetSupportedSensors(compilation_pb2.GetSupportedSensorsRequest())
    return list(r.sensors)


@router.get("/actuators")
async def get_actuators(_=Depends(verify_token)):
    from shared.proto_gen import compilation_pb2
    stub = get_stub("compilation")
    r = await stub.GetSupportedActuators(compilation_pb2.GetSupportedActuatorsRequest())
    return list(r.actuators)


@router.get("/others")
async def get_others(_=Depends(verify_token)):
    from shared.proto_gen import compilation_pb2
    stub = get_stub("compilation")
    r = await stub.GetSupportedOthers(compilation_pb2.GetSupportedOthersRequest())
    return list(r.others)


@router.get("/labels")
async def get_all_labels(_=Depends(verify_token)):
    from shared.proto_gen import compilation_pb2
    stub = get_stub("compilation")
    
    hw_res = await stub.GetSupportedHardware(compilation_pb2.GetSupportedHardwareRequest())
    sensor_res = await stub.GetSupportedSensors(compilation_pb2.GetSupportedSensorsRequest())
    actuator_res = await stub.GetSupportedActuators(compilation_pb2.GetSupportedActuatorsRequest())
    other_res = await stub.GetSupportedOthers(compilation_pb2.GetSupportedOthersRequest())
    
    merged = {}
    merged.update(dict(hw_res.labels))
    merged.update(dict(sensor_res.labels))
    merged.update(dict(actuator_res.labels))
    merged.update(dict(other_res.labels))
    return merged




@router.get("/{device_id}")
async def get_device(device_id: str, _=Depends(verify_token)):
    stub = get_stub("device")
    r = await stub.GetDevice(device_pb2.GetDeviceRequest(id=device_id))
    return {"id": r.id, "name": r.name, "hardware_type": r.hardware_type,
            "description": r.description, "status": r.status, "created_at": r.created_at,
            "sensors": list(r.sensors), "actuators": list(r.actuators), "others": list(r.others)}

@router.delete("/{device_id}", status_code=204)
async def delete_device(device_id: str, _=Depends(verify_token)):
    await get_stub("device").DeleteDevice(device_pb2.DeleteDeviceRequest(id=device_id))

@router.put("/{device_id}")
async def update_device(device_id: str, body: DeviceUpdate, _=Depends(verify_token)):
    stub = get_stub("device")
    r = await stub.UpdateDevice(device_pb2.UpdateDeviceRequest(
        id=device_id, name=body.name, description=body.description))
    return {"id": r.id, "name": r.name, "hardware_type": r.hardware_type,
            "description": r.description, "status": r.status, "created_at": r.created_at,
            "sensors": list(r.sensors), "actuators": list(r.actuators), "others": list(r.others)}

