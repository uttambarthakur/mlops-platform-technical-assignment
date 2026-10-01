from datetime import datetime
from typing import List, Optional
from enum import Enum

from sqlalchemy import ForeignKey, String, Text, TIMESTAMP, Float, Enum as SQLEnum, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass

class LifecycleStage(str, Enum):
    DRAFT = "DRAFT"
    VALIDATED = "VALIDATED"
    APPROVED = "APPROVED"
    STAGING = "STAGING"
    PRODUCTION = "PRODUCTION"
    ARCHIVED = "ARCHIVED"

class MonitoringStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"

class Model(Base):
    __tablename__ = "models"
    
    # Typing without Optional[...] automatically adds NOT NULL to the database columns
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    framework: Mapped[str] = mapped_column(String(100))
    algorithm: Mapped[str] = mapped_column(String(100))
    tags: Mapped[str] = mapped_column(Text)

    
    # Enforces NOT NULL, but auto-generates the timestamp on creation
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    versions: Mapped[List["Version"]] = relationship(
        "Version", 
        back_populates="model", 
        cascade="all, delete-orphan"  # Deleting a model deletes all its versions
    )

class Version(Base):
    __tablename__ = "versions"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    model_id: Mapped[int] = mapped_column(ForeignKey("models.id", ondelete="CASCADE"))
    version_number: Mapped[int] = mapped_column(nullable=False)
    artifact_uri: Mapped[str] = mapped_column(String(255))
    training_data_ref: Mapped[str] = mapped_column(String(255))
    approval_status: Mapped[str] = mapped_column(String(50))
    lifecycle_stage: Mapped[LifecycleStage] = mapped_column(
        SQLEnum(LifecycleStage),
        default=LifecycleStage.DRAFT,
    )
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    model: Mapped["Model"] = relationship("Model", back_populates="versions")
    deployments: Mapped[List["Deployment"]] = relationship(
        "Deployment", 
        back_populates="version", 
        cascade="all, delete-orphan"
    )
    metrics: Mapped[List["Metric"]] = relationship(
        "Metric", 
        back_populates="version", 
        cascade="all, delete-orphan"
    )

class Deployment(Base):
    __tablename__ = "deployments"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    version_id: Mapped[int] = mapped_column(ForeignKey("versions.id", ondelete="CASCADE"))
    environment: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20))
    artifact_uri: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())

    version: Mapped["Version"] = relationship("Version", back_populates="deployments")

class Metric(Base):
    __tablename__ = "metrics"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    version_id: Mapped[int] = mapped_column(ForeignKey("versions.id", ondelete="CASCADE"))
    metric_name: Mapped[str] = mapped_column(String)
    metric_value: Mapped[float] = mapped_column(Float)
    monitoring_status: Mapped[MonitoringStatus] = mapped_column(SQLEnum(MonitoringStatus), default=MonitoringStatus.ACTIVE)

    last_successful_inference: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP)
    recorded_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())

    # Added the relationship back to Version so you can easily query a metric's version
    version: Mapped["Version"] = relationship("Version", back_populates="metrics")
