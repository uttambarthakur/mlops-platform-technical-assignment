from pydantic import BaseModel, ConfigDict, Field, field_validator
from datetime import datetime
from typing import List, Literal, Optional
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
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator("tags", mode="before")
    @classmethod
    def split_tags(cls, value):
        if isinstance(value, str):
            return [tag.strip() for tag in value.split(",") if tag.strip()]
        return value

class VersionSaveRequest(BaseModel):
    artifact_uri: str
    training_data_ref: Optional[str] = None
    approval_status: Optional[str] = None
    lifecycle_stage: LifecycleStage = LifecycleStage.DRAFT

class VersionSaveResponse(VersionSaveRequest):
    model_config = ConfigDict(from_attributes=True)

    id: int
    model_id: int
    version_number: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class VersionApprovalRequest(BaseModel):
    approval_status: Literal["APPROVED", "REJECTED"]

class MetricIngestRequest(BaseModel):
    metric_name: str = Field(min_length=1, max_length=255)
    metric_value: float
    monitoring_status: MonitoringStatus = MonitoringStatus.ACTIVE
    last_successful_inference: Optional[datetime] = None

class MetricBatchIngestRequest(BaseModel):
    metrics: List[MetricIngestRequest] = Field(min_length=1, max_length=500)

class MetricDelta(BaseModel):
    metric_name: str
    version_a_value: Optional[float] = None
    version_b_value: Optional[float] = None
    difference: Optional[float] = None

class VersionComparisonResponse(BaseModel):
    model_id: int
    version_a: VersionSaveResponse
    version_b: VersionSaveResponse
    metric_deltas: List[MetricDelta]

class DeploymentSaveRequest(BaseModel):
    version_id: int
    environment: str

class DeploymentSaveResponse(DeploymentSaveRequest):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    created_at: Optional[datetime] = None

class MetricSaveResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    version_id: int
    metric_name: str
    metric_value: float
    monitoring_status: MonitoringStatus = MonitoringStatus.ACTIVE
    last_successful_inference: Optional[datetime] = None
    recorded_at: Optional[datetime] = None
