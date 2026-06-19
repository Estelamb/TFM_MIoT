import grpc
from sqlalchemy.ext.asyncio import async_sessionmaker
from shared.proto_gen import device_pb2, device_pb2_grpc
from app.repositories.devices import DeviceRepository

def _to_proto(d) -> device_pb2.DeviceResponse:
    res = device_pb2.DeviceResponse(
        id=d.id, name=d.name, hardware_type=d.hardware_type,
        description=d.description or "", status=d.status,
        last_seen_at=d.last_seen_at.isoformat() if d.last_seen_at else "",
        created_at=d.created_at.isoformat(),
    )
    if hasattr(d, 'sensors') and d.sensors:
        res.sensors.extend(d.sensors)
    if hasattr(d, 'actuators') and d.actuators:
        res.actuators.extend(d.actuators)
    if hasattr(d, 'others') and d.others:
        res.others.extend(d.others)
    return res

class DeviceServiceHandler(device_pb2_grpc.DeviceServiceServicer):
    def __init__(self, sf: async_sessionmaker): self._sf = sf

    async def CreateDevice(self, req, ctx):
        async with self._sf() as s:
            d = await DeviceRepository(s).create(
                req.name, req.hardware_type, req.description or None,
                list(req.sensors), list(req.actuators), list(req.others)
            )
            return _to_proto(d)

    async def GetDevice(self, req, ctx):
        async with self._sf() as s:
            d = await DeviceRepository(s).get(req.id)
            if not d: ctx.abort(grpc.StatusCode.NOT_FOUND, "Device not found"); return
            return _to_proto(d)

    async def ListDevices(self, req, ctx):
        async with self._sf() as s:
            devices = await DeviceRepository(s).list_all()
            return device_pb2.ListDevicesResponse(devices=[_to_proto(d) for d in devices])

    async def DeleteDevice(self, req, ctx):
        async with self._sf() as s:
            ok = await DeviceRepository(s).delete(req.id)
            if not ok: ctx.abort(grpc.StatusCode.NOT_FOUND, "Device not found"); return
            return device_pb2.DeleteDeviceResponse(success=True)

    async def UpdateDeviceStatus(self, req, ctx):
        async with self._sf() as s:
            d = await DeviceRepository(s).update_status(req.id, req.status)
            if not d: ctx.abort(grpc.StatusCode.NOT_FOUND, "Device not found"); return
            return _to_proto(d)

    async def UpdateDevice(self, req, ctx):
        async with self._sf() as s:
            d = await DeviceRepository(s).update(req.id, req.name, req.description or None)
            if not d: ctx.abort(grpc.StatusCode.NOT_FOUND, "Device not found"); return
            return _to_proto(d)
