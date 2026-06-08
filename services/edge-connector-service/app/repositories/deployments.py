from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.orm import Deployment, DeviceRef, ModelRef, ScriptRef

class DeploymentRepository:
    def __init__(self, s: AsyncSession): self.s = s

    async def create(self, device_id: str, model_id: str, script_id: str) -> Deployment:
        d = Deployment(device_id=device_id, model_id=model_id, script_id=script_id)
        self.s.add(d); await self.s.commit(); await self.s.refresh(d); return d

    async def get(self, id: str) -> Deployment | None:
        return await self.s.get(Deployment, id)

    async def list_all(self) -> list[Deployment]:
        r = await self.s.execute(select(Deployment).order_by(Deployment.created_at.desc()))
        return list(r.scalars().all())

    async def list_for_device(self, device_id: str) -> list[Deployment]:
        r = await self.s.execute(
            select(Deployment).where(Deployment.device_id == device_id)
            .order_by(Deployment.created_at.desc()))
        return list(r.scalars().all())

    async def mark_sent(self, d: Deployment):
        d.status = "sent"; d.sent_at = datetime.now(timezone.utc)
        await self.s.commit()

    async def mark_running(self, d: Deployment):
        d.status = "running"; d.running_at = datetime.now(timezone.utc)
        await self.s.commit()

    async def mark_failed(self, d: Deployment, error: str):
        d.status = "failed"; d.error_msg = error
        await self.s.commit()

    async def get_device(self, id: str) -> DeviceRef | None:
        return await self.s.get(DeviceRef, id)

    async def get_model(self, id: str) -> ModelRef | None:
        return await self.s.get(ModelRef, id)

    async def get_script(self, id: str) -> ScriptRef | None:
        return await self.s.get(ScriptRef, id)
