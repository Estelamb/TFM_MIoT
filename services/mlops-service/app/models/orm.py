"""
Mirror readonly de la tabla models para tracking de compilación.
El compilation-service no es owner de la tabla, solo lee y actualiza
compile_status via gRPC al ai-service.
"""
import uuid
from datetime import datetime
from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from shared.utils.database import Base

class ModelRef(Base):
    __tablename__ = "models"
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    source_key: Mapped[str] = mapped_column(Text)
    compile_status: Mapped[str] = mapped_column(String)
    hardware_type: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
