from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.orm import Dataset, Model, DatasetVersion


class ModelRepository:
    def __init__(self, s: AsyncSession): self.s = s

    async def create(self, name: str, description: str | None, source_key: str,
                     source_sha256: str, dataset_id: str | None = None,
                     base_architecture: str | None = None, epochs: int | None = None,
                     input_size: str | None = None, batch_size: int | None = None,
                     dataset_version_id: str | None = None) -> Model:
        if dataset_id:
            d = await self.s.get(Dataset, dataset_id)
            if not d:
                raise ValueError("Dataset not found")
        if dataset_version_id:
            dv = await self.s.get(DatasetVersion, dataset_version_id)
            if not dv:
                raise ValueError("Dataset version not found")
        m = Model(
            name=name,
            description=description,
            source_key=source_key,
            source_sha256=source_sha256,
            dataset_id=dataset_id,
            dataset_version_id=dataset_version_id,
            base_architecture=base_architecture,
            epochs=epochs,
            input_size=input_size,
            batch_size=batch_size,
        )
        self.s.add(m); await self.s.commit(); return await self.get(m.id)

    async def get(self, id: str) -> Model | None:
        r = await self.s.execute(
            select(Model)
            .where(Model.id == id)
            .options(selectinload(Model.compilations))
        )
        return r.scalar_one_or_none()

    async def list_all(self) -> list[Model]:
        r = await self.s.execute(
            select(Model)
            .options(selectinload(Model.compilations))
            .order_by(Model.created_at.desc())
        )
        return list(r.scalars().all())

    async def update_compiled(self, id: str, compiled_key: str, compiled_sha256: str,
                               hardware_type: str, compile_status: str, compile_error: str,
                               source_key: str | None = None, source_sha256: str | None = None) -> Model | None:
        m = await self.get(id)
        if not m: return None

        if source_key:
            m.source_key = source_key
        if source_sha256:
            m.source_sha256 = source_sha256

        if hardware_type:
            # If compile_status is ready, update main model fields for backward compatibility.
            # Do NOT update main model status to "compiling" or "failed" to prevent blocking it.
            if compile_status == "ready":
                m.compiled_key = compiled_key or None
                m.compiled_sha256 = compiled_sha256 or None
                m.hardware_type = hardware_type or None
                m.compile_status = "ready"
                m.compile_error = None
            else:
                if m.compile_status not in ("ready", "training"):
                    m.compile_status = "ready"

            from app.models.orm import ModelCompilation
            res = await self.s.execute(
                select(ModelCompilation)
                .where(ModelCompilation.model_id == id)
                .where(ModelCompilation.hardware_type == hardware_type)
            )
            comp = res.scalar_one_or_none()
            if not comp:
                comp = ModelCompilation(
                    model_id=id,
                    hardware_type=hardware_type,
                    compiled_key=compiled_key or "",
                    compiled_sha256=compiled_sha256 or "",
                    compile_status=compile_status,
                    compile_error=compile_error or None
                )
                self.s.add(comp)
            else:
                comp.compiled_key = compiled_key or ""
                comp.compiled_sha256 = compiled_sha256 or ""
                comp.compile_status = compile_status
                comp.compile_error = compile_error or None
        else:
            if compile_status:
                m.compile_status = compile_status
            if compile_error:
                m.compile_error = compile_error or None
            if compiled_key:
                m.compiled_key = compiled_key or None
            if compiled_sha256:
                m.compiled_sha256 = compiled_sha256 or None

        await self.s.commit()
        return await self.get(id)

    async def associate_dataset(self, model_id: str, dataset_id: str, dataset_version_id: str | None = None) -> Model | None:
        m = await self.get(model_id)
        if not m:
            return None
        d = await self.s.get(Dataset, dataset_id)
        if not d:
            raise ValueError("Dataset not found")
        m.dataset_id = d.id
        if dataset_version_id:
            dv = await self.s.get(DatasetVersion, dataset_version_id)
            if not dv or dv.dataset_id != d.id:
                raise ValueError("Dataset version not found or does not belong to this dataset")
            m.dataset_version_id = dv.id
        else:
            m.dataset_version_id = None
        await self.s.commit(); return await self.get(m.id)

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
        await self.s.commit(); return await self.get(id)

    async def delete(self, id: str) -> bool:
        m = await self.get(id)
        if not m: return False
        await self.s.delete(m); await self.s.commit(); return True


class DatasetRepository:
    def __init__(self, s: AsyncSession): self.s = s

    async def create(self, name: str, description: str | None) -> Dataset:
        d = Dataset(name=name, description=description)
        self.s.add(d); await self.s.commit()
        # Fetch again using get() to ensure versions relationship is eager loaded
        return await self.get(d.id)

    async def get(self, id: str) -> Dataset | None:
        r = await self.s.execute(
            select(Dataset)
            .where(Dataset.id == id)
            .options(selectinload(Dataset.versions))
        )
        return r.scalar_one_or_none()

    async def update(self, id: str, name: str, description: str | None) -> Dataset | None:
        d = await self.get(id)
        if not d: return None
        d.name = name
        d.description = description
        await self.s.commit()
        # Fetch again using get() to ensure versions relationship is eager loaded
        return await self.get(id)

    async def set_file(self, dataset_id: str, object_key: str, sha256: str,
                       size_bytes: int, meta_info: dict | None = None,
                       version: str | None = None, description: str | None = None) -> Dataset | None:
        d = await self.s.get(Dataset, dataset_id)
        if not d: return None
        
        # Calculate version name if not provided
        if not version or not version.strip():
            # Query existing versions to find count
            r = await self.s.execute(
                select(DatasetVersion).where(DatasetVersion.dataset_id == dataset_id)
            )
            existing_versions = r.scalars().all()
            version = f"v{len(existing_versions) + 1}"
            
        # Create a new DatasetVersion
        dv = DatasetVersion(
            dataset_id=dataset_id,
            version=version.strip(),
            description=description,
            object_key=object_key,
            sha256=sha256,
            size_bytes=size_bytes,
            meta_info=meta_info
        )
        self.s.add(dv)
        
        # Keep parent dataset columns synced to the latest uploaded version for backward compatibility
        d.object_key = object_key
        d.sha256 = sha256
        d.size_bytes = size_bytes
        if meta_info is not None:
            d.meta_info = meta_info
            
        await self.s.commit()
        
        # Fetch again using get() to ensure versions relationship is eager loaded
        return await self.get(dataset_id)

    async def list_all(self) -> list[Dataset]:
        r = await self.s.execute(
            select(Dataset)
            .options(selectinload(Dataset.versions))
            .order_by(Dataset.created_at.desc())
        )
        return list(r.scalars().all())

    async def delete(self, id: str) -> bool:
        d = await self.get(id)
        if not d:
            return False
        await self.s.delete(d); await self.s.commit(); return True
