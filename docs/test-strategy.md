## Unit Tests
- Domain transitions: Verify lifecycle stage transitions (DRAFT -> VALIDATED -> APPROVED ->  
  STAGING -> PRODUCTION -> ARCHIVED)
- Validation: Ensure unapproved version cannot be promoted to production
- Deployment rules: Confirm idempotency (duplicate requests return same deployment)
- Rollback rules: Validate rollback restores previous state safely
- Metric calculation: Test metric name/value storage and retrieval logic

## API Tests
- Success cases: Register model, register version, approve, deploy, view metrics.
- Invalid requests: Missing fields, invalid IDs, malformed JSON.
- Missing records: Requests for non‑existent model/version/deployment return 404.
- Conflicts: Prevent duplicate names or duplicate deployment requests.
- Duplicates: Idempotent handling of repeated deployment requests.
- Authorization: Role/env claim enforcement (e.g., only admin can deploy to Production).

## Integration Tests
- Persistence: Verify SQLAlchemy + PostgreSQL schema consistency.
- Deployment workflow: Simulate deployment folder creation, status transitions.
- Retry: Ensure failed deployments can be retried successfully.
- Rollback: Confirm rollback restores previous deployment state.
- Metrics: Insert and query flexible name/value metrics, validate API response format.

## Angular Tests
- Components: Model inventory, version details, deployment view, monitoring dashboard.
- Services: API service layer, error handling, observables.
- Loading states: Verify loading, empty, success, and error UI states.
- Validation: Form validation for model/version registration.
- API interaction: Mock backend responses, ensure UI renders correctly.

## End-to-End Scenario
- Register a model.
- Register two versions.
- Approve one version.
- Attempt Production deployment of unapproved version → blocked.
- Deploy approved version → succeeds.
- View metrics in Angular dashboard.
- Simulate failure → retry deployment.
- Roll back Production deployment → previous version restored.

## CI, Coverage and Limitations
- CI/CD: GitHub Actions pipeline runs unit, API, and integration tests on every commit.
- Coverage: Aim for >80% coverage across backend services and API contracts.
- Limitations:

  * JWT auth is demo‑only (local secret, no refresh/revocation).
  * Deployment simulation uses folder creation, not real runtime.
  * Metrics schema flexible but requires pivoting for dashboard views.
  *Angular tests limited to mocked backend responses (no live infra).