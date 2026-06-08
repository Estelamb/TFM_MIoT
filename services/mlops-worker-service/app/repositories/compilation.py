"""
Repositorio de compilación.
Nota: el estado se actualiza via gRPC al ai-service (que es owner de la tabla models).
Este repo solo se usa para lecturas locales de diagnóstico.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.orm import ModelRef

class CompilationRepository:
    def __init__(self, s: AsyncSession): self.s = s

    async def get_model_ref(self, model_id: str) -> ModelRef | None:
        return await self.s.get(ModelRef, model_id)
