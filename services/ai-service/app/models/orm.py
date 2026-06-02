import uuid
from datetime import datetime
from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from shared.utils.database import Base

def _uuid(): return str(uuid.uuid4())

class Model(Base):
    __tablename__ = "models"
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_key: Mapped[str] = mapped_column(Text, nullable=False)
    source_sha256: Mapped[str] = mapped_column(String, nullable=False)
    compiled_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    compiled_sha256: Mapped[str | None] = mapped_column(String, nullable=True)
    hardware_type: Mapped[str | None] = mapped_column(String, nullable=True)
    compile_status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    compile_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
