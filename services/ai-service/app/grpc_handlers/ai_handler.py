import grpc
from sqlalchemy.ext.asyncio import async_sessionmaker
from shared.proto_gen import ai_pb2, ai_pb2_grpc
from app.repositories.models import ModelRepository

def _to_proto(m) -> ai_pb2.ModelResponse:
    return ai_pb2.ModelResponse(
        id=m.id, name=m.name, description=m.description or "",
        source_key=m.source_key, source_sha256=m.source_sha256,
        compiled_key=m.compiled_key or "", compiled_sha256=m.compiled_sha256 or "",
        hardware_type=m.hardware_type or "", compile_status=m.compile_status,
        compile_error=m.compile_error or "", created_at=m.created_at.isoformat(),
    )

class AIServiceHandler(ai_pb2_grpc.AIServiceServicer):
    def __init__(self, sf: async_sessionmaker): self._sf = sf

    async def UploadModel(self, req, ctx):
        async with self._sf() as s:
            m = await ModelRepository(s).create(req.name, req.description or None,
                                                 req.source_key, req.source_sha256)
            return _to_proto(m)

    async def GetModel(self, req, ctx):
        async with self._sf() as s:
            m = await ModelRepository(s).get(req.id)
            if not m: ctx.abort(grpc.StatusCode.NOT_FOUND, "Model not found"); return
            return _to_proto(m)

    async def ListModels(self, req, ctx):
        async with self._sf() as s:
            models = await ModelRepository(s).list_all()
            return ai_pb2.ListModelsResponse(models=[_to_proto(m) for m in models])

    async def DeleteModel(self, req, ctx):
        async with self._sf() as s:
            ok = await ModelRepository(s).delete(req.id)
            if not ok: ctx.abort(grpc.StatusCode.NOT_FOUND, "Model not found"); return
            return ai_pb2.DeleteModelResponse(success=True)

    async def UpdateModelCompiled(self, req, ctx):
        async with self._sf() as s:
            m = await ModelRepository(s).update_compiled(
                req.id, req.compiled_key, req.compiled_sha256,
                req.hardware_type, req.compile_status, req.compile_error)
            if not m: ctx.abort(grpc.StatusCode.NOT_FOUND, "Model not found"); return
            return _to_proto(m)
