import grpc
from sqlalchemy.ext.asyncio import async_sessionmaker
from shared.proto_gen import ai_pb2, ai_pb2_grpc
from app.repositories.models import DatasetRepository, ModelRepository

def _to_proto(m) -> ai_pb2.ModelResponse:
    return ai_pb2.ModelResponse(
        id=m.id, name=m.name, description=m.description or "",
        source_key=m.source_key, source_sha256=m.source_sha256,
        compiled_key=m.compiled_key or "", compiled_sha256=m.compiled_sha256 or "",
        hardware_type=m.hardware_type or "", compile_status=m.compile_status,
        compile_error=m.compile_error or "", created_at=m.created_at.isoformat(),
        dataset_id=m.dataset_id or "", dataset_version_id=m.dataset_version_id or "",
    )


def _dataset_to_proto(d) -> ai_pb2.DatasetResponse:
    return ai_pb2.DatasetResponse(
        id=d.id,
        name=d.name,
        description=d.description or "",
        created_at=d.created_at.isoformat(),
    )


def _dataset_version_to_proto(v, model_ids: list[str] | None = None) -> ai_pb2.DatasetVersionResponse:
    return ai_pb2.DatasetVersionResponse(
        id=v.id,
        dataset_id=v.dataset_id,
        version=v.version,
        description=v.description or "",
        object_key=v.object_key,
        sha256=v.sha256,
        size_bytes=v.size_bytes,
        created_at=v.created_at.isoformat(),
        model_ids=model_ids or [],
    )

class AIServiceHandler(ai_pb2_grpc.AIServiceServicer):
    def __init__(self, sf: async_sessionmaker): self._sf = sf

    async def UploadModel(self, req, ctx):
        async with self._sf() as s:
            try:
                m = await ModelRepository(s).create(
                    req.name,
                    req.description or None,
                    req.source_key,
                    req.source_sha256,
                    req.dataset_version_id or None,
                )
            except ValueError as e:
                ctx.abort(grpc.StatusCode.NOT_FOUND, str(e)); return
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

    async def UploadDataset(self, req, ctx):
        async with self._sf() as s:
            d = await DatasetRepository(s).create(req.name, req.description or None)
            return _dataset_to_proto(d)

    async def GetDataset(self, req, ctx):
        async with self._sf() as s:
            d = await DatasetRepository(s).get(req.id)
            if not d: ctx.abort(grpc.StatusCode.NOT_FOUND, "Dataset not found"); return
            return _dataset_to_proto(d)

    async def ListDatasets(self, req, ctx):
        async with self._sf() as s:
            items = await DatasetRepository(s).list_all()
            return ai_pb2.ListDatasetsResponse(datasets=[_dataset_to_proto(d) for d in items])

    async def DeleteDataset(self, req, ctx):
        async with self._sf() as s:
            ok = await DatasetRepository(s).delete(req.id)
            if not ok: ctx.abort(grpc.StatusCode.NOT_FOUND, "Dataset not found"); return
            return ai_pb2.DeleteDatasetResponse(success=True)

    async def UploadDatasetVersion(self, req, ctx):
        async with self._sf() as s:
            try:
                v = await DatasetRepository(s).create_version(
                    req.dataset_id,
                    req.version,
                    req.description or None,
                    req.object_key,
                    req.sha256,
                    req.size_bytes,
                )
            except ValueError as e:
                ctx.abort(grpc.StatusCode.NOT_FOUND, str(e)); return
            return _dataset_version_to_proto(v)

    async def GetDatasetVersion(self, req, ctx):
        async with self._sf() as s:
            repo = DatasetRepository(s)
            v = await repo.get_version(req.id)
            if not v: ctx.abort(grpc.StatusCode.NOT_FOUND, "Dataset version not found"); return
            model_ids = await repo.list_model_ids_for_version(v.id)
            return _dataset_version_to_proto(v, model_ids=model_ids)

    async def ListDatasetVersions(self, req, ctx):
        async with self._sf() as s:
            repo = DatasetRepository(s)
            versions = await repo.list_versions(req.dataset_id)
            result = []
            for v in versions:
                model_ids = await repo.list_model_ids_for_version(v.id)
                result.append(_dataset_version_to_proto(v, model_ids=model_ids))
            return ai_pb2.ListDatasetVersionsResponse(versions=result)

    async def AssociateModelDatasetVersion(self, req, ctx):
        async with self._sf() as s:
            try:
                m = await ModelRepository(s).associate_dataset_version(
                    req.model_id, req.dataset_version_id
                )
            except ValueError as e:
                ctx.abort(grpc.StatusCode.NOT_FOUND, str(e)); return
            if not m: ctx.abort(grpc.StatusCode.NOT_FOUND, "Model not found"); return
            return _to_proto(m)
