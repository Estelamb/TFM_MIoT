from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.orm import Dataset, Model


class ModelRepository:
    def __init__(self, s: AsyncSession): self.s = s

    async def create(self, name: str, description: str | None, source_key: str,
                     source_sha256: str, dataset_id: str | None = None,
                     base_architecture: str | None = None, epochs: int | None = None,
                     input_size: str | None = None, batch_size: int | None = None) -> Model:
        if dataset_id:
            d = await self.s.get(Dataset, dataset_id)
            if not d:
                raise ValueError("Dataset not found")
        m = Model(
            name=name,
            description=description,
            source_key=source_key,
            source_sha256=source_sha256,
            dataset_id=dataset_id,
            base_architecture=base_architecture,
            epochs=epochs,
            input_size=input_size,
            batch_size=batch_size,
        )
        self.s.add(m); await self.s.commit(); await self.s.refresh(m); return m

    async def get(self, id: str) -> Model | None:
        return await self.s.get(Model, id)

    async def list_all(self) -> list[Model]:
        r = await self.s.execute(select(Model).order_by(Model.created_at.desc()))
        return list(r.scalars().all())

    async def update_compiled(self, id: str, compiled_key: str, compiled_sha256: str,
                               hardware_type: str, compile_status: str, compile_error: str,
                               source_key: str | None = None, source_sha256: str | None = None) -> Model | None:
        m = await self.get(id)
        if not m: return None
        m.compiled_key = compiled_key or None
        m.compiled_sha256 = compiled_sha256 or None
        m.hardware_type = hardware_type or None
        m.compile_status = compile_status
        m.compile_error = compile_error or None
        if source_key:
            m.source_key = source_key
        if source_sha256:
            m.source_sha256 = source_sha256
        await self.s.commit(); await self.s.refresh(m); return m

    async def associate_dataset(self, model_id: str, dataset_id: str) -> Model | None:
        m = await self.get(model_id)
        if not m:
            return None
        d = await self.s.get(Dataset, dataset_id)
        if not d:
            raise ValueError("Dataset not found")
        m.dataset_id = d.id
        await self.s.commit(); await self.s.refresh(m); return m

    async def update(self, id: str, name: str, description: str | None,
                     epochs: int | None = None, input_size: str | None = None,
                     batch_size: int | None = None,
                     base_architecture: str | None = None) -> Model | None:
        m = await self.get(id)
        if not m: return None
        m.name = name
        m.description = description
        if epochs is not None:
            m.epochs = epochs
        if input_size is not None:
            m.input_size = input_size
        if batch_size is not None:
            m.batch_size = batch_size
        if base_architecture is not None:
            m.base_architecture = base_architecture
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

    async def update(self, id: str, name: str, description: str | None) -> Dataset | None:
        d = await self.get(id)
        if not d: return None
        d.name = name
        d.description = description
        await self.s.commit(); await self.s.refresh(d); return d

    async def set_file(self, dataset_id: str, object_key: str, sha256: str,
                       size_bytes: int, meta_info: dict | None = None) -> Dataset | None:
        d = await self.get(dataset_id)
        if not d: return None
        d.object_key = object_key
        d.sha256 = sha256
        d.size_bytes = size_bytes
        if meta_info is not None:
            d.meta_info = meta_info
        await self.s.commit(); await self.s.refresh(d); return d

    async def list_all(self) -> list[Dataset]:
        r = await self.s.execute(select(Dataset).order_by(Dataset.created_at.desc()))
        return list(r.scalars().all())

    async def delete(self, id: str) -> bool:
        d = await self.get(id)
        if not d:
            return False
        await self.s.delete(d); await self.s.commit(); return True
