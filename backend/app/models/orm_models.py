from datetime import datetime
from typing import List
from sqlalchemy import ForeignKey, String, Text, TIMESTAMP, Float, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class Model(Base):
    __tablename__ = "models"
    
    # Typing without Optional[...] automatically adds NOT NULL to the database columns
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    framework: Mapped[str] = mapped_column(String)
    algorithm: Mapped[str] = mapped_column(String)
    tags: Mapped[str] = mapped_column(Text)
    
    # Enforces NOT NULL, but auto-generates the timestamp on creation
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())

    versions: Mapped[List["Version"]] = relationship(
        "Version", 
        back_populates="model", 
        cascade="all, delete-orphan"  # Deleting a model deletes all its versions
    )

class Version(Base):
    __tablename__ = "versions"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    model_id: Mapped[int] = mapped_column(ForeignKey("models.id", ondelete="CASCADE"))
    artifact_uri: Mapped[str] = mapped_column(String)
    training_data_ref: Mapped[str] = mapped_column(String)
    approval_status: Mapped[str] = mapped_column(String)
    lifecycle_stage: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())

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
    environment: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())

    version: Mapped["Version"] = relationship("Version", back_populates="deployments")

class Metric(Base):
    __tablename__ = "metrics"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    version_id: Mapped[int] = mapped_column(ForeignKey("versions.id", ondelete="CASCADE"))
    metric_name: Mapped[str] = mapped_column(String)
    metric_value: Mapped[float] = mapped_column(Float)
    recorded_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())

    # Added the relationship back to Version so you can easily query a metric's version
    version: Mapped["Version"] = relationship("Version", back_populates="metrics")
