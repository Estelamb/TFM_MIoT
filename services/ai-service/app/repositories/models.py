from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.orm import Model

class ModelRepository:
    def __init__(self, s: AsyncSession): self.s = s

    async def create(self, name: str, description: str | None, source_key: str, source_sha256: str) -> Model:
        m = Model(name=name, description=description, source_key=source_key, source_sha256=source_sha256)
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

    async def delete(self, id: str) -> bool:
        m = await self.get(id)
        if not m: return False
        await self.s.delete(m); await self.s.commit(); return True
