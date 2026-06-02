from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.orm import Device

class DeviceRepository:
    def __init__(self, s: AsyncSession): self.s = s

    async def create(self, name: str, hardware_type: str, description: str | None) -> Device:
        d = Device(name=name, hardware_type=hardware_type, description=description)
        self.s.add(d); await self.s.commit(); await self.s.refresh(d); return d

    async def get(self, id: str) -> Device | None:
        return await self.s.get(Device, id)

    async def list_all(self) -> list[Device]:
        r = await self.s.execute(select(Device).order_by(Device.created_at.desc()))
        return list(r.scalars().all())

    async def update_status(self, id: str, status: str) -> Device | None:
        d = await self.get(id)
        if not d: return None
        d.status = status
        d.last_seen_at = datetime.now(timezone.utc)
        await self.s.commit(); await self.s.refresh(d); return d

    async def delete(self, id: str) -> bool:
        d = await self.get(id)
        if not d: return False
        await self.s.delete(d); await self.s.commit(); return True
