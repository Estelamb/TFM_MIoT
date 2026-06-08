from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.orm import Script

class ScriptRepository:
    def __init__(self, s: AsyncSession): self.s = s

    async def create(self, name: str, description: str | None, hardware_type: str,
                     script_key: str, script_sha256: str) -> Script:
        sc = Script(name=name, description=description, hardware_type=hardware_type,
                    script_key=script_key, script_sha256=script_sha256)
        self.s.add(sc); await self.s.commit(); await self.s.refresh(sc); return sc

    async def get(self, id: str) -> Script | None:
        return await self.s.get(Script, id)

    async def list_all(self) -> list[Script]:
        r = await self.s.execute(select(Script).order_by(Script.created_at.desc()))
        return list(r.scalars().all())

    async def delete(self, id: str) -> bool:
        sc = await self.get(id)
        if not sc: return False
        await self.s.delete(sc); await self.s.commit(); return True
