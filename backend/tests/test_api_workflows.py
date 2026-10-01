import asyncio
from pathlib import Path

from sqlalchemy import func, select

from app.api.v1 import minimum
from app.models.orm_models import Deployment, LifecycleStage, Model, Version
from app.services import artifact_manager
from app.services.artifact_manager import ArtifactManager

from conftest import ApiHarness, seed_model_and_versions


def test_version_approval_requires_approver_and_updates_lifecycle(api: ApiHarness):
    model_id, version_id, _ = asyncio.run(seed_model_and_versions(api.sessions))
    path = f"/api/v1/models/{model_id}/versions/{version_id}/approval"

    assert api.client.post(path, json={"approval_status": "APPROVED"}).status_code == 403

    response = api.client.post(
        path,
        json={"approval_status": "APPROVED"},
        headers=api.auth("approver"),
    )

    assert response.status_code == 200
    assert response.json()["approval_status"] == "APPROVED"
    assert response.json()["lifecycle_stage"] == "APPROVED"


def test_metrics_can_be_ingested_and_compared(api: ApiHarness):
    model_id, version_a_id, version_b_id = asyncio.run(seed_model_and_versions(api.sessions))
    headers = api.auth("operator")

    for version_id, value in ((version_a_id, 24.5), (version_b_id, 19.0)):
        response = api.client.post(
            f"/api/v1/models/{model_id}/versions/{version_id}/metrics",
            headers=headers,
            json={"metrics": [{"metric_name": "latency_ms", "metric_value": value}]},
        )
        assert response.status_code == 201
        assert len(response.json()) == 1

    comparison = api.client.get(
        f"/api/v1/models/{model_id}/versions/compare",
        params={"version_a_id": version_a_id, "version_b_id": version_b_id},
    )

    assert comparison.status_code == 200
    assert comparison.json()["metric_deltas"] == [
        {
            "metric_name": "latency_ms",
            "version_a_value": 24.5,
            "version_b_value": 19.0,
            "difference": -5.5,
        }
    ]


def test_deployment_idempotency_key_returns_existing_deployment(api: ApiHarness, monkeypatch):
    _, _, approved_version_id = asyncio.run(seed_model_and_versions(api.sessions))

    async def no_op_finalize(*args, **kwargs):
        return None

    monkeypatch.setattr(minimum, "finalize_deployment", no_op_finalize)
    headers = {**api.auth("operator"), "Idempotency-Key": "deployment-request-1"}
    payload = {"version_id": approved_version_id, "environment": "staging"}
    first = api.client.post("/api/v1/deployments", json=payload, headers=headers)
    second = api.client.post("/api/v1/deployments", json=payload, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]

    different_payload = {"version_id": approved_version_id, "environment": "testing"}
    conflict = api.client.post(
        "/api/v1/deployments",
        json=different_payload,
        headers=headers,
    )
    assert conflict.status_code == 409

    async def count_deployments() -> int:
        async with api.sessions() as session:
            return await session.scalar(select(func.count()).select_from(Deployment))

    assert asyncio.run(count_deployments()) == 1


def test_production_deployment_requires_admin_and_approved_version(api: ApiHarness, monkeypatch):
    _, pending_version_id, approved_version_id = asyncio.run(seed_model_and_versions(api.sessions))

    async def no_op_finalize(*args, **kwargs):
        return None

    monkeypatch.setattr(minimum, "finalize_deployment", no_op_finalize)
    missing_key = api.client.post(
        "/api/v1/deployments",
        json={"version_id": approved_version_id, "environment": "production"},
        headers=api.auth("admin"),
    )
    assert missing_key.status_code == 422

    unauthorized = api.client.post(
        "/api/v1/deployments",
        json={"version_id": approved_version_id, "environment": "production"},
        headers={**api.auth("operator"), "Idempotency-Key": "prod-operator"},
    )
    assert unauthorized.status_code == 403

    unapproved = api.client.post(
        "/api/v1/deployments",
        json={"version_id": pending_version_id, "environment": "production"},
        headers={**api.auth("admin"), "Idempotency-Key": "prod-unapproved"},
    )
    assert unapproved.status_code == 400


def test_artifact_version_number_increments_from_latest_version(api, tmp_path, monkeypatch):
    async def seed_existing_version() -> None:
        async with api.sessions() as session:
            model = Model(
                id=37,
                name="High ID Model",
                framework="test",
                algorithm="test",
                tags="",
            )
            session.add(model)
            session.add(
                Version(
                    model_id=37,
                    version_number=1,
                    artifact_uri="old-artifact",
                    training_data_ref="train-v1",
                    approval_status="PENDING",
                    lifecycle_stage=LifecycleStage.DRAFT,
                )
            )
            await session.commit()

    asyncio.run(seed_existing_version())
    monkeypatch.setattr(artifact_manager, "ARTIFACTS_DIR", tmp_path / "artifacts")
    source = tmp_path / "model.bin"
    source.write_bytes(b"test-model")

    async def save_next_version() -> tuple[str, str]:
        async with api.sessions() as session:
            return await ArtifactManager.save_version_file(37, "High ID Model", source, session)

    artifact_uri, version_label = asyncio.run(save_next_version())

    assert version_label == "v2"
    assert Path(artifact_uri).read_bytes() == b"test-model"