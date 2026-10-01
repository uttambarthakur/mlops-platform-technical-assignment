import hashlib
import json
import tempfile
from typing import List
from pathlib import Path
import random
import asyncio

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Header, HTTPException, Request, UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import select

from app.models.schemas import (
    DeploymentSaveRequest,
    DeploymentSaveResponse,
    MetricBatchIngestRequest,
    MetricDelta,
    MetricSaveResponse,
    ModelSaveRequest,
    ModelSaveResponse,
    VersionApprovalRequest,
    VersionComparisonResponse,
    VersionSaveResponse,
)
from app.models.orm_models import Deployment, IdempotencyRecord, LifecycleStage, Metric, Model, MonitoringStatus, Version
from app.main import AsyncSessionLocal, get_db
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

    filename = Path(file.filename).name
    if not filename:
        raise HTTPException(status_code=400, detail="Uploaded file must have a filename")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir) / filename
        temp_path.write_bytes(await file.read())
        try:
            artifact_uri, version_label = await ArtifactManager.save_version_file(
                model.id, model.name, temp_path, db
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save version: {str(e)}") from e

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


@router.get("/models/{model_id}/versions", response_model=List[VersionSaveResponse])
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


@router.post(
    "/models/{model_id}/versions/{version_id}/approval",
    response_model=VersionSaveResponse,
)
async def update_version_approval(
    model_id: int,
    version_id: int,
    decision: VersionApprovalRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    if request.state.claims.get("role") != "approver":
        raise HTTPException(status_code=403, detail="Only approvers can update version approval")

    result = await db.execute(
        select(Version).where(Version.id == version_id, Version.model_id == model_id)
    )
    version = result.scalar_one_or_none()
    if version is None:
        raise HTTPException(status_code=404, detail="Model version not found")
    if version.lifecycle_stage == LifecycleStage.ARCHIVED:
        raise HTTPException(status_code=409, detail="Archived versions cannot be approved")

    version.approval_status = decision.approval_status
    if decision.approval_status == "APPROVED":
        version.lifecycle_stage = LifecycleStage.APPROVED
    await db.commit()
    await db.refresh(version)
    return version


@router.get(
    "/models/{model_id}/versions/compare",
    response_model=VersionComparisonResponse,
)
async def compare_model_versions(
    model_id: int,
    version_a_id: int,
    version_b_id: int,
    db: AsyncSession = Depends(get_db),
):
    if version_a_id == version_b_id:
        raise HTTPException(status_code=400, detail="Choose two different versions to compare")

    model = await db.get(Model, model_id)
    if model is None:
        raise HTTPException(status_code=404, detail="Model not found")

    result = await db.execute(
        select(Version).where(
            Version.model_id == model_id,
            Version.id.in_([version_a_id, version_b_id]),
        )
    )
    versions = {version.id: version for version in result.scalars().all()}
    if len(versions) != 2:
        raise HTTPException(status_code=404, detail="One or both model versions were not found")

    result = await db.execute(
        select(Metric)
        .where(Metric.version_id.in_([version_a_id, version_b_id]))
        .order_by(Metric.recorded_at.desc(), Metric.id.desc())
    )
    latest_metrics: dict[tuple[int, str], float] = {}
    for metric in result.scalars().all():
        latest_metrics.setdefault((metric.version_id, metric.metric_name), metric.metric_value)

    metric_names = sorted({name for _, name in latest_metrics})
    metric_deltas = []
    for metric_name in metric_names:
        value_a = latest_metrics.get((version_a_id, metric_name))
        value_b = latest_metrics.get((version_b_id, metric_name))
        metric_deltas.append(
            MetricDelta(
                metric_name=metric_name,
                version_a_value=value_a,
                version_b_value=value_b,
                difference=value_b - value_a if value_a is not None and value_b is not None else None,
            )
        )

    return VersionComparisonResponse.model_validate(
        {
            "model_id": model_id,
            "version_a": versions[version_a_id],
            "version_b": versions[version_b_id],
            "metric_deltas": metric_deltas,
        }
    )

def simulate_deployment_status() -> str:
    # 70% chance succeed, 30% chance fail
    return "SUCCEEDED" if random.random() < 0.7 else "FAILED"

async def finalize_deployment(
    deployment_id: int,
    version_id: int,
    artifact_uri: str,
    environment: str,
    session_factory: async_sessionmaker[AsyncSession],
    delay: int = 5,
):
    # Wait before updating (simulate deployment time)
    await asyncio.sleep(delay)

    async with session_factory() as db:
        deployment = await db.get(Deployment, deployment_id)
        if not deployment:
            return

        try:
            final_status = simulate_deployment_status()
            if final_status == "SUCCEEDED":
                deployed_path = await ArtifactManager.deploy_version(version_id, artifact_uri, environment)
                deployment.artifact_uri = deployed_path
            else:
                deployment.artifact_uri = artifact_uri

            deployment.status = final_status
            await db.commit()
        except Exception as error:
            await db.rollback()
            deployment.status = "FAILED"
            await db.commit()
            logger.error("Deployment %s failed: %s", deployment_id, error)

@router.post("/deployments", response_model=DeploymentSaveResponse)
async def save_deployment(
    deployment: DeploymentSaveRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    idempotency_key: str = Header(..., min_length=1, max_length=128, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db)
):
    # Check if version exists
    result = await db.execute(select(Version).where(Version.id == deployment.version_id))
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    if deployment.environment.lower() == "production":
        if request.state.claims.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Only admin can deploy to production")
        if (version.approval_status or "").upper() != "APPROVED":
            raise HTTPException(status_code=400, detail="Only approved versions can be deployed to production")

    request_hash = hashlib.sha256(
        json.dumps(
            {
                "version_id": deployment.version_id,
                "environment": deployment.environment.strip().lower(),
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    key = idempotency_key.strip()
    if not key:
        raise HTTPException(status_code=400, detail="Idempotency-Key cannot be blank")
    existing_record = await db.get(IdempotencyRecord, key)
    if existing_record is not None:
        if existing_record.request_hash != request_hash:
            raise HTTPException(status_code=409, detail="Idempotency-Key was already used for another request")
        existing_deployment = await db.get(Deployment, existing_record.deployment_id)
        if existing_deployment is not None:
            return existing_deployment

    # Create new deployment with initial status
    new_deployment = Deployment(
        version_id=deployment.version_id,
        environment=deployment.environment,
        artifact_uri=version.artifact_uri,  # initial reference
        status="DEPLOYING"
    )
    db.add(new_deployment)
    await db.flush()
    db.add(
        IdempotencyRecord(
            idempotency_key=key,
            request_hash=request_hash,
            deployment_id=new_deployment.id,
        )
    )
    try:
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        existing_record = await db.get(IdempotencyRecord, key)
        if existing_record is not None and existing_record.request_hash == request_hash:
            existing_deployment = await db.get(Deployment, existing_record.deployment_id)
            if existing_deployment is not None:
                return existing_deployment
        raise HTTPException(status_code=409, detail="Deployment request conflicts with existing data") from e
    await db.refresh(new_deployment)

    # Schedule background task to simulate file movement + status update
    background_tasks.add_task(
        finalize_deployment,
        new_deployment.id,
        version.id,
        version.artifact_uri,
        deployment.environment,
        AsyncSessionLocal,
        delay=5
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
        AsyncSessionLocal,
        delay=5
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
@router.post(
    "/models/{model_id}/versions/{version_id}/metrics",
    response_model=List[MetricSaveResponse],
    status_code=201,
)
async def ingest_version_metrics(
    model_id: int,
    version_id: int,
    payload: MetricBatchIngestRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    if request.state.claims.get("role") not in {"admin", "operator"}:
        raise HTTPException(status_code=403, detail="Metric ingestion requires admin or operator role")

    result = await db.execute(
        select(Version).where(Version.id == version_id, Version.model_id == model_id)
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Model version not found")

    records = [
        Metric(
            version_id=version_id,
            metric_name=item.metric_name,
            metric_value=item.metric_value,
            monitoring_status=MonitoringStatus(item.monitoring_status.value),
            last_successful_inference=item.last_successful_inference,
        )
        for item in payload.metrics
    ]
    db.add_all(records)
    await db.commit()
    for record in records:
        await db.refresh(record)
    return records


@router.get("/models/{model_id}/metrics", response_model=List[MetricSaveResponse])
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