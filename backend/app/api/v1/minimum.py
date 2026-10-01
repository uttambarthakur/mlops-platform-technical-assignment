from typing import List
from pathlib import Path
import random
import asyncio

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.schemas import ModelSaveRequest, ModelSaveResponse, DeploymentSaveRequest, DeploymentSaveResponse, VersionSaveRequest, VersionSaveResponse, MetricSaveResponse
from app.models.orm_models import Model, Metric, Deployment, Version
from app.main import get_db
from app.services.artifact_manager import ArtifactManager
from app.services.log_manager import get_logger

router = APIRouter()
logger = get_logger("minimum_v1")

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

@router.post("/models/{model_id}/versions", response_model=VersionSaveResponse)
async def save_model_version(
    model_id: int,
    file: UploadFile = File(...),
    training_data_ref: str = Form(...),
    approval_status: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    # Check if parent model exists
    result = await db.execute(select(Model).where(Model.id == model_id))
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    if not file.filename:
        raise HTTPException(status_code=400, detail="Uploaded file must have a filename")

    # Save uploaded file temporarily
    temp_path = Path(f"/tmp/{file.filename}")
    with temp_path.open("wb") as buffer:
        buffer.write(await file.read())

    artifact_uri = None
    version_label = None

    try:
        artifact_uri, version_label = await ArtifactManager.save_version_file(
            model.id, model.name, temp_path, db
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save version: {str(e)}")
    finally:
        temp_path.unlink(missing_ok=True)

    if not artifact_uri or not version_label:
        raise HTTPException(status_code=500, detail="Artifact manager did not return valid paths")

    new_version = Version(
        model_id=model.id,
        version_number=int(version_label.strip("v")),
        artifact_uri=artifact_uri,
        training_data_ref=training_data_ref,
        approval_status=approval_status,
        lifecycle_stage="DRAFT"
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

def simulate_deployment_status() -> str:
    # 70% chance succeed, 30% chance fail
    return "SUCCEEDED" if random.random() < 0.7 else "FAILED"

async def finalize_deployment(deployment_id: int, version_id: int, artifact_uri: str, environment: str, db: AsyncSession, delay: int = 5):
    # Wait before updating (simulate deployment time)
    await asyncio.sleep(delay)

    # Re-fetch deployment
    deployment = await db.get(Deployment, deployment_id)
    if not deployment:
        return

    try:
        # Try moving the artifact into deployments/{env}/
        final_status = simulate_deployment_status()
        if final_status == "SUCCEEDED":
            deployed_path = await ArtifactManager.deploy_version(version_id, artifact_uri, environment)
            deployment.artifact_uri = deployed_path
        else:
            # On failure, keep artifact_uri unchanged
            deployment.artifact_uri = artifact_uri

        deployment.status = final_status
        await db.commit()
        await db.refresh(deployment)

        print(f"Deployment {deployment_id} finalized with status {final_status}")
    except Exception as e:
        # If file movement fails, mark as FAILED
        deployment.status = "FAILED"
        await db.commit()
        await db.refresh(deployment)
        print(f"Deployment {deployment_id} failed due to error: {e}")

@router.post("/deployments", response_model=DeploymentSaveResponse)
async def save_deployment(
    deployment: DeploymentSaveRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    # Check if version exists
    result = await db.execute(select(Version).where(Version.id == deployment.version_id))
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    # Create new deployment with initial status
    new_deployment = Deployment(
        version_id=deployment.version_id,
        environment=deployment.environment,
        artifact_uri=version.artifact_uri,  # initial reference
        status="DEPLOYING"
    )
    db.add(new_deployment)
    await db.commit()
    await db.refresh(new_deployment)

    # Schedule background task to simulate file movement + status update
    background_tasks.add_task(
        finalize_deployment,
        new_deployment.id,
        version.id,
        version.artifact_uri,
        deployment.environment,
        db,
        delay=120
    )

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
async def retry_deployment(
    deployment_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    deployment = await db.get(Deployment, deployment_id)
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")

    deployment.status = "RETRYING"
    await db.commit()
    await db.refresh(deployment)

    # Schedule background task to retry deployment
    result = await db.execute(select(Version).where(Version.id == deployment.version_id))
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    background_tasks.add_task(
        finalize_deployment,
        deployment.id,
        version.id,
        version.artifact_uri,
        deployment.environment,
        db,
        delay=60
    )

    return deployment


@router.post("/deployments/{deployment_id}/rollback", response_model=DeploymentSaveResponse)
async def rollback_deployment(deployment_id: int, db: AsyncSession = Depends(get_db)):
    deployment = await db.get(Deployment, deployment_id)
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")

    try:
        rollback_path = await ArtifactManager.rollback_deployment(deployment.id, deployment.artifact_uri)
        deployment.artifact_uri = rollback_path
        deployment.status = "ROLLED_BACK"
        await db.commit()
        await db.refresh(deployment)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rollback failed: {str(e)}")

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