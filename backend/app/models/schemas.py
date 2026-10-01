from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
from enum import Enum


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

class ModelSaveRequest(BaseModel):
    name: str
    framework: str
    algorithm: str
    tags: List[str]

class ModelSaveResponse(ModelSaveRequest):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class VersionSaveRequest(BaseModel):
    artifact_uri: str
    training_data_ref: Optional[str] = None
    approval_status: Optional[str] = None
    lifecycle_stage: LifecycleStage = LifecycleStage.DRAFT

class VersionSaveResponse(VersionSaveRequest):
    id: int
    model_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class DeploymentSaveRequest(BaseModel):
    version_id: int
    environment: str

class DeploymentSaveResponse(DeploymentSaveRequest):
    id: int
    status: str
    created_at: Optional[datetime] = None

class MetricSaveResponse(BaseModel):
    id: int
    version_id: int
    metric_name: str
    metric_value: float
    monitoring_status: MonitoringStatus = MonitoringStatus.ACTIVE
    last_successful_inference: Optional[datetime] = None
    recorded_at: Optional[datetime] = None
