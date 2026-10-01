## Context
The platform exposes REST APIs for model registry, version management, deployments, monitoring, and health. The design emphasizes resource‑oriented endpoints, typed requests/responses, validation, idempotency, and governance enforcement.

## Scope
- Model registration and versioning
- Approval and lifecycle promotion
- Deployment workflows (request, retry, rollback)
- Monitoring metrics
- Health check

## Design Principles
- **Resource‑oriented**: Models, versions, deployments, metrics are first‑class resources.  
- **Typed contracts**: Pydantic schemas enforce request/response validation.  
- **Governance**: Middleware enforces role/env claims.  
- **Idempotency**: Duplicate deployment requests are safely handled.  
- **Observability**: Correlation IDs and structured errors returned consistently.  

---

## Endpoints

### Models
- `POST /models`  
  **Request**:  
  ```json
  {
    "name": "predictive-maintenance",
    "framework": "scikit-learn",
    "algorithm": "random-forest",
    "tags": ["maintenance", "industrial"],
    "metadata": {"owner": "teamA"}
  }
  ```  
  **Response**:  
  ```json
  {
    "id": 1,
    "name": "predictive-maintenance",
    "framework": "scikit-learn",
    "algorithm": "random-forest",
    "tags": ["maintenance", "industrial"],
    "metadata": {"owner": "teamA"},
    "created_at": "2026-10-01T00:00:00Z"
  }
  ```

- `GET /models` → List all models.  
- `GET /models/{model_id}` → Retrieve model details.

### Versions
- `POST /models/{model_id}/versions`  
  **Request**:  
  ```json
  {
    "artifact_uri": "s3://bucket/model-v1.pkl",
    "training_data_ref": "s3://bucket/train.csv",
    "approval_status": "DRAFT",
    "lifecycle_stage": "VALIDATED"
  }
  ```  
  **Response**:  
  ```json
  {
    "id": 101,
    "model_id": 1,
    "artifact_uri": "s3://bucket/model-v1.pkl",
    "training_data_ref": "s3://bucket/train.csv",
    "approval_status": "DRAFT",
    "lifecycle_stage": "VALIDATED",
    "created_at": "2026-10-01T00:00:00Z"
  }
  ```

- `GET /models/{model_id}/versions` → List versions.
- `POST /models/{model_id}/versions/{version_id}/approval` → Approve or reject a version. Requires the `approver` role.
- `GET /models/{model_id}/versions/compare?version_a_id={id}&version_b_id={id}` → Compare two versions and their latest metric values.

### Deployments
- `POST /deployments`  
  Requires an `Idempotency-Key` header. Replaying the same key and payload returns the existing deployment; reusing a key with a different payload returns `409 Conflict`.
  **Request**:  
  ```json
  {
    "version_id": 101,
    "environment": "production"
  }
  ```  
  **Response**:  
  ```json
  {
    "id": 5001,
    "version_id": 101,
    "environment": "production",
    "status": "REQUESTED",
    "created_at": "2026-10-01T00:00:00Z"
  }
  ```

- `GET /deployments` → List deployments.  
- `GET /deployments/{deployment_id}` → Deployment details.  
- `POST /deployments/{deployment_id}/retry` → Retry failed deployment.  
- `POST /deployments/{deployment_id}/rollback` → Roll back deployment.

### Metrics
- `POST /models/{model_id}/versions/{version_id}/metrics` → Ingest a batch of metric observations. Requires the `admin` or `operator` role.
- `GET /models/{model_id}/metrics` → List recorded metric observations.
- `GET /models/{model_id}/metrics`  
  **Response**:  
  ```json
  {
  "model_id": 101,
  "metrics": [
    {
      "metric_name": "latency_ms",
      "metric_value": 25.4,
      "recorded_at": "2026-09-30T23:59:00Z"
    },
    {
      "metric_name": "throughput_rps",
      "metric_value": 120,
      "recorded_at": "2026-09-30T23:59:00Z"
    },
    {
      "metric_name": "error_rate",
      "metric_value": 0.01,
      "recorded_at": "2026-09-30T23:59:00Z"
    },
    {
      "metric_name": "drift_score",
      "metric_value": 0.05,
      "recorded_at": "2026-09-30T23:59:00Z"
    },
    {
      "metric_name": "quality_score",
      "metric_value": 0.92,
      "recorded_at": "2026-09-30T23:59:00Z"
    }
   ]
  }
```

### Health
- `GET /health` → `{ "status": "ok" }`

---

## Governance Rules
- **Approval Workflow**: Only `APPROVED` versions can be deployed to Production.  
- **Role Enforcement**:  
  - `admin` → Production deployments, rollback.  
  - `approver` → Approve/register versions.  
  - `operator` → Retry/rollback deployments.  
- **Idempotency**: Duplicate deployment requests return existing deployment record.  
- **Concurrency**: DB transactions ensure safe promotion/rollback.  

---

## Error Handling
- Consistent error format:  
  ```json
  {
    "error": "Forbidden",
    "detail": "Only admin can deploy to production",
    "correlation_id": "abc123"
  }
  ```
