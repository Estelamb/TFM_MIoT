import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from shared.utils.database import Base

def _uuid(): return str(uuid.uuid4())

# Readonly refs (solo para FK integrity, no gestiona estas tablas)
class DeviceRef(Base):
    __tablename__ = "devices"
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    hardware_type: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)

class ModelRef(Base):
    __tablename__ = "models"
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    compiled_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    compiled_sha256: Mapped[str | None] = mapped_column(String, nullable=True)
    compile_status: Mapped[str] = mapped_column(String)

class ScriptRef(Base):
    __tablename__ = "scripts"
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    script_key: Mapped[str] = mapped_column(Text)
    script_sha256: Mapped[str] = mapped_column(String)

class Deployment(Base):
    __tablename__ = "deployments"
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    device_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("devices.id"), nullable=False)
    model_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("models.id"), nullable=False)
    script_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("scripts.id"), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    running_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_msg: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
