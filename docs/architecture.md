## Context
The MLOps demo platform must demonstrate production‑quality engineering practices for model lifecycle management. The focus is on architecture, governance, observability, and scalability rather than sophisticated ML training.

## Scope
The platform supports
- Model and version registration
- Approval and lifecycle promotion
- Deployment requests, status tracking, retry, rollback
- Monitoring of latency, throughput, drift, error rate, availability
- Angular based operational views
- Governance and observability features (auth, audit, metrics)

## Architecture Overview
The system is modular, service oriented application:
- Angular UI -> Operational dashboards and workflows
- Fastapi Backend -> REST APIs, governance enforcement
- Domain Services -> Model registry, deployment manager, monitoring service
- Persistence Layer -> PostgreSQL (via SQLAlchemy + Alembic)
- Worker/Queue -> Async deployment simualtion (Fastapi background tasks or asyncio queue)
- Monitoring -> Metrics endpoints, structures logs, correlation IDs
- Authentication Boundaries -> JWT with local secrets, role/env/exp claims
- External Runtime (simulated) -> Deployment folder inside backend container

## Components
- UI Layer: Angular + Angular Material + RxJS
- API Layer: FastAPI routers (models, versions, deployments, metrics)
- Domain Layer: Services for approval workflow, idempotency, rollback safety
- Persistence: PostgreSQL container, Alembic migrations
- Async Worker: Background tasks / asyncio queue for deployment lifecycle
- Observability: Logging, health/readiness endpoints, metrics
- Auth: JWT middleware enforcing role/env claims

## Domain Model
Entities:
- Model: id, name, framework, algorithm, tags
- Version: id, model_id, artifact_uri, training_data_ref, approval_status, lifecycle_stage
- Deployment: id, version_id, environment, status, history
- Metrics: id, version_id, metric_name, metric_value, recorded_at

## Key Workflows
- Register model + versions
- Approve version
- Prevent unapproved promotion
- Deploy approved version (async)
- Retry failed deployment
- Roll back production deployment
- Show monitoring metrics in UI
- Handle duplicate requests safely

## Reliability
- Idempotency enforced at deployment API
- Rollback safety via deployment history
- Health/readiness endpoints for liveness checks
- Structured error handling with consistent responses

## Security
- JWT with role, env, exp claims
- Governance middleware enforcing promotion controls
- Audit logging with correlation IDs
- Role‑based authorization (admin, approver, operator)

## Observability
- Structured logs (logging)
- Correlation IDs per request
- Metrics endpoint (/models/{model_id}/metrics)
- Health (/health) checks

## Scaling
Not implemented in demo application:
- PostgreSQL partitioning for large metric volumes
- Redis/Celery for async deployments
- Kubernetes manifests for horizontal scaling
- Modular routers for clear ownership boundaries
- Caching layer (Redis) for frequently accessed metadata

## Trade-offs
- Local JWT vs OAuth: Simpler demo, but lacks refresh/revocation. ADR documents migration path.
- Folder‑based deployment simulation vs real runtime: Lightweight for demo, but not production‑ready.
- Postgres choice: Cloud Postgres (Database as a Service) for scale.
- FastAPI background tasks vs Celery: Background tasks are simpler, Celery scales better.
- .create_all in lifespan is for demo simplicity. In production, rely on Alembic migration instead.