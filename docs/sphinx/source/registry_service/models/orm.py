import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, func, BigInteger, ARRAY
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from shared.utils.database import Base

def _uuid(): return str(uuid.uuid4())

class Device(Base):
    __tablename__ = "devices"
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String, nullable=False)
    hardware_type: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="offline")
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    sensors: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, server_default='{}')
    actuators: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, server_default='{}')
    others: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, server_default='{}')

class Dataset(Base):
    __tablename__ = "datasets"
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    object_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    sha256: Mapped[str | None] = mapped_column(String, nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    meta_info: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    models: Mapped[list["Model"]] = relationship(back_populates="dataset")
    versions: Mapped[list["DatasetVersion"]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan", order_by="DatasetVersion.created_at.desc()"
    )

class DatasetVersion(Base):
    __tablename__ = "dataset_versions"
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    dataset_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    object_key: Mapped[str] = mapped_column(Text, nullable=False)
    sha256: Mapped[str] = mapped_column(String, nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    meta_info: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    dataset: Mapped["Dataset"] = relationship(back_populates="versions")

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
    dataset_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("datasets.id", ondelete="SET NULL"), nullable=True
    )
    dataset_version_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("dataset_versions.id", ondelete="SET NULL"), nullable=True
    )
    base_architecture: Mapped[str | None] = mapped_column(String, nullable=True)
    epochs: Mapped[int | None] = mapped_column(nullable=True)
    input_size: Mapped[str | None] = mapped_column(String, nullable=True)
    batch_size: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    dataset: Mapped["Dataset | None"] = relationship(back_populates="models")
    compilations: Mapped[list["ModelCompilation"]] = relationship(
        back_populates="model", cascade="all, delete-orphan", order_by="ModelCompilation.created_at.desc()"
    )

class ModelCompilation(Base):
    __tablename__ = "model_compilations"
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    model_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("models.id", ondelete="CASCADE"), nullable=False
    )
    hardware_type: Mapped[str] = mapped_column(String, nullable=False)
    compiled_key: Mapped[str] = mapped_column(Text, nullable=False)
    compiled_sha256: Mapped[str] = mapped_column(String, nullable=False)
    compile_status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    compile_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    model: Mapped["Model"] = relationship(back_populates="compilations")

class Script(Base):
    __tablename__ = "scripts"
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str] = mapped_column(String, nullable=False)
    script_key: Mapped[str] = mapped_column(Text, nullable=False)
    script_sha256: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
