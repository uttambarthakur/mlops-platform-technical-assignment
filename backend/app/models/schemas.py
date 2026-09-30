from pydantic import BaseModel
from datetime import datetime
from typing import List

class ModelSaveRequest(BaseModel):
    name: str
    framework: str
    algorithm: str
    tags: List[str]

class ModelSaveResponse(ModelSaveRequest):
    id: int
    created_at: datetime | None = None

class VersionSaveRequest(BaseModel):
    artifact_uri: str
    training_data_ref: str
    approval_status: str
    lifecycle_stage: str

class VersionSaveResponse(VersionSaveRequest):
    id: int
    model_id: int
    created_at: datetime | None = None

class DeploymentSaveRequest(BaseModel):
    version_id: int
    environment: str

class DeploymentSaveResponse(DeploymentSaveRequest):
    id: int
    status: str
    created_at: datetime | None = None

class MetricSaveResponse(BaseModel):
    metric_name: str
    metric_value: float
    recorded_at: datetime | None = None
