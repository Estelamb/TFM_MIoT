from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.orm import Dataset, DatasetVersion, Model

class ModelRepository:
    def __init__(self, s: AsyncSession): self.s = s

    async def create(self, name: str, description: str | None, source_key: str,
                     source_sha256: str, dataset_version_id: str | None = None) -> Model:
        dataset_id: str | None = None
        if dataset_version_id:
            dv = await self.s.get(DatasetVersion, dataset_version_id)
            if not dv:
                raise ValueError("Dataset version not found")
            dataset_id = dv.dataset_id
        m = Model(
            name=name,
            description=description,
            source_key=source_key,
            source_sha256=source_sha256,
            dataset_id=dataset_id,
            dataset_version_id=dataset_version_id,
        )
        self.s.add(m); await self.s.commit(); await self.s.refresh(m); return m

    async def get(self, id: str) -> Model | None:
        return await self.s.get(Model, id)

    async def list_all(self) -> list[Model]:
        r = await self.s.execute(select(Model).order_by(Model.created_at.desc()))
        return list(r.scalars().all())

    async def update_compiled(self, id: str, compiled_key: str, compiled_sha256: str,
                               hardware_type: str, compile_status: str, compile_error: str) -> Model | None:
        m = await self.get(id)
        if not m: return None
        m.compiled_key = compiled_key or None
        m.compiled_sha256 = compiled_sha256 or None
        m.hardware_type = hardware_type or None
        m.compile_status = compile_status
        m.compile_error = compile_error or None
        await self.s.commit(); await self.s.refresh(m); return m

    async def associate_dataset_version(self, model_id: str, dataset_version_id: str) -> Model | None:
        m = await self.get(model_id)
        if not m:
            return None
        dv = await self.s.get(DatasetVersion, dataset_version_id)
        if not dv:
            raise ValueError("Dataset version not found")
        m.dataset_version_id = dv.id
        m.dataset_id = dv.dataset_id
        await self.s.commit(); await self.s.refresh(m); return m

    async def delete(self, id: str) -> bool:
        m = await self.get(id)
        if not m: return False
        await self.s.delete(m); await self.s.commit(); return True


class DatasetRepository:
    def __init__(self, s: AsyncSession): self.s = s

    async def create(self, name: str, description: str | None) -> Dataset:
        d = Dataset(name=name, description=description)
        self.s.add(d); await self.s.commit(); await self.s.refresh(d); return d

    async def get(self, id: str) -> Dataset | None:
        return await self.s.get(Dataset, id)

    async def list_all(self) -> list[Dataset]:
        r = await self.s.execute(select(Dataset).order_by(Dataset.created_at.desc()))
        return list(r.scalars().all())

    async def delete(self, id: str) -> bool:
        d = await self.get(id)
        if not d:
            return False
        await self.s.delete(d); await self.s.commit(); return True

    async def create_version(self, dataset_id: str, version: str, description: str | None,
                             object_key: str, sha256: str, size_bytes: int) -> DatasetVersion:
        d = await self.get(dataset_id)
        if not d:
            raise ValueError("Dataset not found")
        v = DatasetVersion(
            dataset_id=dataset_id,
            version=version,
            description=description,
            object_key=object_key,
            sha256=sha256,
            size_bytes=size_bytes,
        )
        self.s.add(v); await self.s.commit(); await self.s.refresh(v); return v

    async def get_version(self, id: str) -> DatasetVersion | None:
        return await self.s.get(DatasetVersion, id)

    async def list_versions(self, dataset_id: str) -> list[DatasetVersion]:
        r = await self.s.execute(
            select(DatasetVersion)
            .where(DatasetVersion.dataset_id == dataset_id)
            .order_by(DatasetVersion.created_at.desc())
        )
        return list(r.scalars().all())

    async def list_model_ids_for_version(self, dataset_version_id: str) -> list[str]:
        r = await self.s.execute(
            select(Model.id).where(Model.dataset_version_id == dataset_version_id)
        )
        return list(r.scalars().all())
