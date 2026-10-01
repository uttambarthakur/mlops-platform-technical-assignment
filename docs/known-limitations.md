## Authentication
- JWTs are signed with a local secret for demo purposes.  
- No refresh tokens, revocation, or external identity provider integration.  
- Shared secret distribution is insecure in real deployments.

## Deployment Simulation
- Deployments are simulated via folder creation and status transitions.  
- No actual model runtime or container orchestration is invoked.  
- Rollback and retry logic operate on simulated state only.

## Metrics
- Metrics can be ingested through a protected API and are stored as name/value pairs.  
- No inference pipeline currently generates telemetry; metrics must be submitted by an external producer.

## Observability
- Logging and correlation IDs are implemented, but no external monitoring stack (Prometheus, 
  Grafana, OpenTelemetry) is integrated.  
- Health check endpoint is basic and not tied to container orchestration probes.

## Governance
- Role enforcement is demo‑only via JWT claims (`role`, `env`, `exp`).  
- No real approval workflow integration with external systems.  
- Limited to three roles (admin, approver, operator).

## Scaling
- PostgreSQL schema designed for extensibility, but not load‑tested at scale.  
- Background tasks simulate async deployments; no production‑grade queue (Celery/Redis/Kafka).  

## Angular Frontend
- Approval, metric-ingestion, and version-comparison controls are integrated; API authorization still requires a valid demo JWT.  
- No production build optimizations (e.g., caching, CDN).  
- Limited error handling for network failures.

## CI/CD
- GitHub Actions pipeline runs unit/integration tests, but no full staging/production deployment 
  pipeline.  
- Coverage target is >80%, but not all edge cases are covered.  
