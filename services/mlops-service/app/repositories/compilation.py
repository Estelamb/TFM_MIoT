"""
Compilation repository.
Note: Status is updated via gRPC to the ai-service (which is the owner of the models table).
This repository is only used for local diagnostic reads.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.orm import ModelRef

class CompilationRepository:
    def __init__(self, s: AsyncSession): self.s = s

    async def get_model_ref(self, model_id: str) -> ModelRef | None:
        return await self.s.get(ModelRef, model_id)
