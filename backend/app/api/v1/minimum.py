from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.schemas import ModelSaveRequest, ModelSaveResponse, DeploymentSaveRequest, DeploymentSaveResponse, VersionSaveRequest, VersionSaveResponse, MetricSaveResponse
from app.models.orm_models import Model, Metric, Deployment, Version
from app.main import get_db

router = APIRouter()


# Models
@router.post("/models", response_model=ModelSaveResponse)
async def save_model(model: ModelSaveRequest, db: AsyncSession = Depends(get_db)):
    new_model = Model(name=model.name, framework=model.framework, algorithm=model.algorithm, tags=', '.join(model.tags))
    db.add(new_model)
    await db.commit()
    await db.refresh(new_model)
    return new_model

    
@router.get("/models", response_model=List[ModelSaveResponse])
async def get_models(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Model))
    models = result.scalars().all()
    return models

@router.get("/models/{model_id}", response_model=ModelSaveResponse)
async def get_model(model_id: int, db: AsyncSession = Depends(get_db)):
    model = await db.get(Model, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return model

# Versions
@router.post("/models/{model_id}/versions", response_model=VersionSaveResponse)
async def save_model_version(model_id: int, version: VersionSaveRequest, db: AsyncSession = Depends(get_db)):
    # Check if parent model exists
    result = await db.execute(select(Model).where(Model.id == model_id))
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    # Create new version
    new_version = Version(
        model_id=model_id,
        artifact_uri=version.artifact_uri,
        training_data_ref=version.training_data_ref,
        approval_status=version.approval_status,
        lifecycle_stage=version.lifecycle_stage
    )
    db.add(new_version)
    await db.commit()
    await db.refresh(new_version)
    return new_version

@router.get("/models/{model_id}/versions", response_model=VersionSaveResponse)
async def get_model_versions(model_id: int, db: AsyncSession = Depends(get_db)):
    # check if model exists
    result = await db.execute(select(Model).where(Model.id == model_id))
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    # Fetch versions
    result = await db.execute(select(Version).where(Version.model_id == model_id))
    versions = result.scalars().all()
    return versions

# Deployments
@router.post("/deployments", response_model=DeploymentSaveResponse)
async def save_deployment(deployment: DeploymentSaveRequest, db: AsyncSession = Depends(get_db)):
    # Check if version exists
    result = await db.execute(select(Version).where(Version.id == deployment.version_id))
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    # Create new deployment
    new_deployment = Deployment(
        version_id=deployment.version_id,
        environment=deployment.environment,
        status="DEPLOYING"  # initial status
    )
    db.add(new_deployment)
    await db.commit()
    await db.refresh(new_deployment)
    return new_deployment

@router.get("/deployments", response_model=List[DeploymentSaveResponse])
async def get_deployments(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Deployment))
    deployments = result.scalars().all()
    return deployments

@router.get("/deployments/{deployment_id}", response_model=DeploymentSaveResponse)
async def get_deployment(deployment_id: int, db: AsyncSession = Depends(get_db)):
    deployment = await db.get(Deployment, deployment_id)
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    return deployment

@router.post("/deployments/{deployment_id}/retry", response_model=DeploymentSaveResponse)
async def retry_deployment(deployment_id: int, db: AsyncSession = Depends(get_db)):
    deployment = await db.get(Deployment, deployment_id)
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")

    deployment.status = "RETRYING"
    await db.commit()
    await db.refresh(deployment)
    return deployment


@router.post("/deployments/{deployment_id}/rollback", response_model=DeploymentSaveResponse)
async def rollback_deployment(deployment_id: int, db: AsyncSession = Depends(get_db)):
    deployment = await db.get(Deployment, deployment_id)
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")

    # Update status to simulate rollback
    deployment.status = "ROLLED_BACK"
    await db.commit()
    await db.refresh(deployment)
    return deployment

# Metrics
@router.get("/models/{model_id}/metrics", response_model=ModelSaveResponse)
async def get_model_metrics(model_id: int, db: AsyncSession = Depends(get_db)):
    # Governance: check if model exists
    result = await db.execute(select(Model).where(Model.id == model_id))
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    # Fetch metrics for all versions of this model
    result = await db.execute(
        select(Metric).join(Model.versions).where(Model.id == model_id)
    )
    metrics = result.scalars().all()
    return metrics

# Health
@router.get("/health")
def health() -> dict:
    return {"status": "ok"}