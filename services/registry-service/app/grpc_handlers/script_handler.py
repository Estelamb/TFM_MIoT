import grpc
from sqlalchemy.ext.asyncio import async_sessionmaker
from shared.proto_gen import script_pb2, script_pb2_grpc
from app.repositories.scripts import ScriptRepository

def _to_proto(sc) -> script_pb2.ScriptResponse:
    return script_pb2.ScriptResponse(
        id=sc.id, name=sc.name, description=sc.description or "",
        language=sc.language, script_key=sc.script_key,
        script_sha256=sc.script_sha256, created_at=sc.created_at.isoformat(),
    )

class ScriptServiceHandler(script_pb2_grpc.ScriptServiceServicer):
    def __init__(self, sf: async_sessionmaker): self._sf = sf

    async def UploadScript(self, req, ctx):
        async with self._sf() as s:
            sc = await ScriptRepository(s).create(req.name, req.description or None,
                                                   req.language,
                                                   req.script_key, req.script_sha256)
            return _to_proto(sc)

    async def GetScript(self, req, ctx):
        async with self._sf() as s:
            sc = await ScriptRepository(s).get(req.id)
            if not sc: ctx.abort(grpc.StatusCode.NOT_FOUND, "Script not found"); return
            return _to_proto(sc)

    async def ListScripts(self, req, ctx):
        async with self._sf() as s:
            scripts = await ScriptRepository(s).list_all()
            return script_pb2.ListScriptsResponse(scripts=[_to_proto(sc) for sc in scripts])

    async def DeleteScript(self, req, ctx):
        async with self._sf() as s:
            ok = await ScriptRepository(s).delete(req.id)
            if not ok: ctx.abort(grpc.StatusCode.NOT_FOUND, "Script not found"); return
            return script_pb2.DeleteScriptResponse(success=True)
