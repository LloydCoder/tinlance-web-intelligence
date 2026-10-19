# W15 Enterprise Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver all repository-verifiable W7–W15 controls and an honest fail-closed readiness decision, without claiming unobserved deployment or governance evidence.

**Architecture:** Extend the existing FastAPI, durable job, PostgreSQL/SQLite, artifact, metrics, and outbox boundaries. TWI stores monitor definitions and run outcomes; existing jobs carry work and Agent OS remains the recurrence owner. Add validated trace propagation, pinned consumer contracts, deterministic evidence tooling, and CI checks while keeping deployment approvals external.

**Tech Stack:** Python 3.12+, FastAPI, PostgreSQL/psycopg, SQLite test backend, pytest, Prometheus, OpenTelemetry API/SDK, JSON Schema, GitHub Actions, shell/PowerShell validation.

**Spec:** `docs/superpowers/specs/2026-10-19-w15-enterprise-readiness-design.md`

## Global Constraints

- Require Python `>=3.12`; full CI matrix is Python 3.12 and 3.13.
- Agent Platform remains identity, authorization, policy and approval authority; derive tenant and subject only from the verified principal.
- Agent OS owns recurrence; TWI exposes explicit monitor operations and does not schedule recurring work.
- TWI change results are bounded observations; they do not establish truth or mutate World Intelligence canonical state.
- Propagate validated W3C `traceparent`; do not propagate baggage by default or place sensitive/high-cardinality data in telemetry.
- Retention remains dry-run by default; destructive cleanup requires the least-privilege maintenance DSN and explicit confirmation.
- W15 gates are `pass`, `fail`, or `not_evidenced`; no deployment, threshold, branch-rule, risk-acceptance, or GA evidence may be invented.

## Review Focus

- URL redirect or DNS rebinding to a private address must fail before fetch and must not leak URL query values into telemetry.
- Cross-tenant monitor, run, artifact, pause, and delete requests must return the existing non-disclosure authorization response.
- Reusing an idempotency key with a different monitor/run request must fail without duplicating work or changing state.
- Concurrent or failed captures must never overwrite a newer successful baseline or advance baseline state on failure.
- Missing, expired, hash-mismatched, revision-mismatched, or non-passing external evidence must keep W15 readiness false.

---

### Task 1: Persistence contracts and monitor migrations

**Files:**
- Create: `src/tinlance_web_intelligence/monitors/__init__.py`
- Create: `src/tinlance_web_intelligence/monitors/model.py`
- Create: `src/tinlance_web_intelligence/persistence/monitor_protocol.py`
- Create: `src/tinlance_web_intelligence/persistence/sqlite_monitors.py`
- Create: `src/tinlance_web_intelligence/persistence/postgres_monitors.py`
- Create: `src/tinlance_web_intelligence/persistence/migrations/002_monitors.sql`
- Create: `db/migrations/002_monitors.sql`
- Modify: `src/tinlance_web_intelligence/persistence/factory.py`
- Modify: `scripts/check_migration_sync.py`
- Test: `tests/test_monitors_repository.py`
- Test: `tests/test_monitor_migration.py`
- Test: `tests/test_postgres_persistence.py`
- Test: `tests/test_migration_runner.py`

**Interfaces:**
- Produce immutable `Monitor(monitor_id, tenant_id, subject_id, target_url, policy, status, baseline_digest, baseline_observed_at, baseline_version, created_at, updated_at, idempotency_key)` and `MonitorRunResult(monitor_id, job_id, outcome, previous_digest, current_digest, changed, observed_at, changed_units)` models.
- Produce `MonitorRepository.create(*, tenant_id: str, subject_id: str, target_url: str, policy: dict[str, object], idempotency_key: str) -> Monitor`, `get(*, tenant_id: str, subject_id: str, monitor_id: str, administrative: bool = False) -> Monitor | None`, `set_status(...) -> Monitor`, `commit_successful_run(..., expected_baseline_version: int, result: MonitorRunResult) -> Monitor`, `record_run_result(...) -> None`, `close() -> None`, and `metrics_snapshot() -> dict[str, float]`.
- The SQLite and PostgreSQL implementations must satisfy the same protocol; PostgreSQL is selected with `database_url`, SQLite only outside production.

- [x] **Step 1: Write repository contract tests** for idempotent replay, idempotency conflict, tenant/subject read isolation, and baseline advancement.
- [x] **Step 2: Run the focused repository tests** with `pytest tests/test_monitors_repository.py -q`; confirmed the tests failed because the monitor module was absent, then passed after implementation.
- [x] **Step 3: Implement monitor models and protocol** with typed enums and SHA-256/count bounds.
- [x] **Step 4: Implement SQLite persistence** with transaction-protected idempotency and baseline version compare-and-set.
- [x] **Step 5: Add synchronized PostgreSQL migration files** and update the migration-sync checker and migration README.
- [x] **Step 6: Implement PostgreSQL persistence** with transaction-protected idempotency and baseline compare-and-set semantics.
- [x] **Step 7: Wire `create_monitor_repository(settings)`** in the persistence factory.
- [x] **Step 8: Run repository/migration tests, migration sync, Ruff and mypy.** Local result: `9 passed, 6 skipped`; all PostgreSQL integration tests were skipped because no PostgreSQL DSN was configured and Docker is unavailable. Runtime migration rollback remains unverified and is left as deployment/CI evidence.
- [x] **Step 9: Commit** as `feat: add durable monitor persistence` (`ae99ec2`).

### Task 2: Monitor capture and baseline service

**Files:**
- Create: `src/tinlance_web_intelligence/monitors/service.py`
- Modify: `src/tinlance_web_intelligence/acquisition/service.py`
- Modify: `src/tinlance_web_intelligence/jobs/model.py`
- Modify: `src/tinlance_web_intelligence/jobs/worker.py`
- Modify: `src/tinlance_web_intelligence/jobs/repository.py`
- Modify: `src/tinlance_web_intelligence/persistence/postgres_jobs.py`
- Test: `tests/test_monitor_service.py`
- Test: `tests/test_worker.py`
- Test: `tests/test_jobs_repository.py`
- Test: `tests/test_postgres_persistence.py`

**Interfaces:**
- Produce `MonitorService.create_monitor(principal, request, idempotency_key) -> Monitor`, `enqueue_run(principal, monitor_id, idempotency_key) -> Job`, `apply_capture(*, monitor: Monitor, job: Job, extracted_text: str, observed_at: datetime) -> MonitorRunResult`, `pause(principal, monitor_id) -> Monitor`, and `resume(principal, monitor_id) -> Monitor`.
- Add `traceparent: str | None` to internal job creation and immutable job model; existing callers may omit it.
- Monitor run jobs use kind `monitor`; worker dispatch consumes `MonitorService` and writes the bounded result into the existing durable job result contract.

- [x] **Step 1: Write service and worker tests** for baseline establishment, deterministic normalized-text comparison, failed/stale/future capture behavior, traceparent persistence/privacy, and pause behavior for an already leased run.
- [x] **Step 2: Run focused tests** and observe expected failures for the absent service, missing monitor job support, future timestamps, and pause incorrectly stopping a leased capture.
- [x] **Step 3: Add monitor job kind support** to SQLite and PostgreSQL job schemas, migrations, adapters, and worker dispatch while preserving existing job handling.
- [x] **Step 4: Implement `MonitorService`** with safe acquisition injection, Unicode/whitespace normalization, SHA-256 digesting, bounded result metadata, idempotent queue requests, and baseline compare-and-set.
- [x] **Step 5: Add optional traceparent persistence** to both job adapters and omit it from public job serialization.
- [x] **Step 6: Run monitor and job regression tests, Ruff and mypy.** Result: 17 passed, 6 PostgreSQL tests skipped because no test DSN was available; lint and typing passed.
- [x] **Step 7: Commit** as `feat: add deterministic monitor capture lifecycle` (`7502d56`).

### Task 3: Versioned monitor API and Platform authorization

**Files:**
- Create: `src/tinlance_web_intelligence/api/http/routes/monitors.py`
- Modify: `src/tinlance_web_intelligence/api/http/app.py`
- Modify: `src/tinlance_web_intelligence/persistence/protocols.py`
- Modify: `src/tinlance_web_intelligence/auth/principal.py`
- Create: `docs/api/monitors-v1.md`
- Test: `tests/test_api_monitors.py`
- Test: `tests/test_platform_tool_catalog.py`
- Test: `tests/test_auth_jwks.py`

**Interfaces:**
- Expose `POST /v1/monitors`, `GET /v1/monitors/{monitor_id}`, `POST /v1/monitors/{monitor_id}/runs`, `GET /v1/monitors/{monitor_id}/runs/{job_id}`, and POST `pause`, `resume`, and `delete` actions.
- Request and response models use Pydantic fields with explicit maximum lengths and forbid unknown fields; handlers derive tenant and subject from `request.state.principal` and existing admin scopes.
- Enqueue responds `202` with the existing job response fields and `Location`; read responses do not include raw page text or URL query values.

- [x] **Step 1: Write API tests** for valid lifecycle, required idempotency headers, scope denial, cross-tenant non-disclosure, unknown fields, blocked URLs, paused-run denial, repeated identical requests, idempotency conflicts, and response privacy.
- [x] **Step 2: Run `pytest tests/test_api_monitors.py -q`** and confirm route/contract failures.
- [x] **Step 3: Implement Pydantic request/response models and route dependencies** using the existing verified principal, admin-scope helper, job repository, monitor repository, and application state conventions.
- [x] **Step 4: Wire repositories and service in `create_app`** with shutdown handling matching current job/outbox lifecycle.
- [x] **Step 5: Add tool catalog/schema entries** for monitor create/read/run/pause/resume and document the separately scoped delete action; preserve compatibility of existing tool names and schemas.
- [x] **Step 6: Run API, auth, and catalog tests** with `pytest tests/test_api_monitors.py tests/test_auth_jwks.py tests/test_platform_tool_catalog.py -q`; validate generated OpenAPI in test mode and ensure docs remain disabled in production.
- [x] **Step 7: Commit** as `feat: expose tenant-scoped monitor API` (`862f98d`).

Ruling: no external Platform SDK revision was available in this checkout; monitor tool manifests were checked against the local typed catalog and consumer revision status remains `not_evidenced`.

### Task 4: End-to-end trace propagation and bounded telemetry

**Files:**
- Modify: `pyproject.toml`
- Create: `src/tinlance_web_intelligence/observability/tracing.py`
- Modify: `src/tinlance_web_intelligence/api/http/app.py`
- Modify: `src/tinlance_web_intelligence/jobs/worker.py`
- Modify: `src/tinlance_web_intelligence/browser/broker_api.py`
- Modify: `src/tinlance_web_intelligence/browser/broker_client.py`
- Modify: `src/tinlance_web_intelligence/integrations/world_intelligence/client.py`
- Modify: `src/tinlance_web_intelligence/config.py`
- Modify: `.env.example`
- Modify: `deployments/compose/staging.yml`
- Test: `tests/test_observability.py`
- Test: `tests/test_browser_broker.py`
- Test: `tests/test_world_intelligence_client.py`

**Interfaces:**
- Add `extract_valid_traceparent(headers: Mapping[str, str]) -> str | None`, `inject_traceparent(headers: MutableMapping[str, str], traceparent: str | None) -> None`, and `start_span(name: str, attributes: Mapping[str, str])` helpers.
- Spans use only bounded operation/component/outcome/error-class attributes; the exporter is disabled unless an approved endpoint is explicitly configured.

- [ ] **Step 1: Write propagation and privacy tests** for valid/invalid versioned `traceparent`, omitted baggage, API-to-job-to-worker continuation, browser broker and WI export propagation, exporter unavailable behavior, and absence of URLs, query values, tokens, tenant/subject IDs, request IDs, or page text in spans.
- [x] **Step 2: Run trace tests** with `pytest tests/test_observability.py tests/test_browser_broker.py tests/test_world_intelligence_client.py -q`; confirm trace propagation tests fail before implementation.
- [ ] **Step 3: Add pinned OpenTelemetry API/SDK dependencies** and implement no-op-safe tracer helpers with W3C Trace Context validation and explicit exporter configuration. API dependency and spans are present; SDK/exporter endpoint setup is not.
- [ ] **Step 4: Instrument request, worker, browser, and export boundaries** while preserving current Prometheus cardinality restrictions and adding bounded provider/browser/worker outcome and duration metrics. Span boundaries are present; separate worker/browser/provider metrics are not.
- [x] **Step 5: Run targeted observability/security checks** with the focused pytest command, `ruff check src tests`, and `mypy src`; confirm no sensitive attribute names/values enter telemetry.
- [x] **Step 6: Commit** as `feat: propagate privacy-safe distributed traces` (`b90ee3a`).

Ruling: tracing defaults to the OpenTelemetry no-op provider; no exporter endpoint, credentials, or approved collector were supplied. No independent worker metrics listener was added, so exporter configuration and worker/provider metric scraping remain open.

### Task 5: Exact-revision consumer compatibility contracts

**Files:**
- Create: `contracts/consumer-matrix.json`
- Create: `contracts/fixtures/platform/<revision>/tool-catalog.json`
- Create: `contracts/fixtures/world-intelligence/<revision>/source-evidence.json`
- Create: `contracts/fixtures/tsic/<revision>/conformance.json`
- Create: `scripts/validate_consumer_contracts.py`
- Modify: `.github/workflows/ci.yml`
- Modify: `src/tinlance_web_intelligence/integrations/agent_platform/tool_catalog.py`
- Modify: `schemas/mcp-tools/`
- Test: `tests/test_consumer_contracts.py`
- Test: `tests/test_platform_tool_catalog.py`
- Test: `tests/test_world_intelligence_client.py`

**Interfaces:**
- Matrix records consumer name, repository, exact immutable revision, contract/schema version, fixture path, and evidence reference; unknown or symbolic revisions such as `main` are invalid.
- Validator entry point: `python scripts/validate_consumer_contracts.py --matrix contracts/consumer-matrix.json` with nonzero exit on missing fixture, schema incompatibility, or revision drift.

- [x] **Step 1: Record and test the currently evidenced consumer revisions**; where an exact external revision cannot be verified from repository evidence, encode the gate as `not_evidenced` rather than guessing a revision.
- [x] **Step 2: Add positive and negative contract tests** for tool names/schemas, World Intelligence observation export, tenant isolation, scope denial, and backward-compatible additive evidence fields.
- [x] **Step 3: Implement the matrix validator** with immutable revision format checks, exact fixture matching, and stable machine-readable output. External schema compatibility remains unverified where no consumer snapshot exists.
- [x] **Step 4: Add the validator to CI** and run `python scripts/validate_consumer_contracts.py --matrix contracts/consumer-matrix.json` plus the focused pytest tests; verify intentional incompatible fixtures fail.
- [x] **Step 5: Document the snapshot refresh/review process** so external consumer revisions change only with owner review and compatibility evidence.
- [x] **Step 6: Commit** as `ci: verify pinned ecosystem consumer contracts` (`038766f`).

### Task 6: Deterministic W15 evidence pack and readiness validator

**Files:**
- Create: `schemas/w15-evidence-pack.schema.json`
- Create: `docs/readiness/w15-gates.json`
- Create: `scripts/build_w15_evidence_pack.py`
- Create: `scripts/validate_w15_evidence_pack.py`
- Create: `tests/fixtures/w15-evidence-pack/`
- Test: `tests/test_w15_evidence_pack.py`
- Modify: `.github/workflows/release.yml`
- Modify: `Makefile`

**Interfaces:**
- Evidence item fields: `gate`, `status` (`pass|fail|not_evidenced`), `owner`, UTC `observed_at`, `source_revision`, `evidence_reference`, `sha256`, and optional `expires_at`.
- Builder entry point: `python scripts/build_w15_evidence_pack.py --gates docs/readiness/w15-gates.json --output dist/w15-evidence-pack.json`.
- Validator entry point: `python scripts/validate_w15_evidence_pack.py --pack dist/w15-evidence-pack.json --revision <full-git-sha>`; exit 0 only for structurally valid repository checks while reporting `ready=false` for any missing external gate.

- [x] **Step 1: Write schema and validator tests** for deterministic ordering/bytes, exact status enum, required gates, expiration, source-revision mismatch, content hash mismatch, unsafe metadata/secret patterns, and fail-closed readiness.
- [x] **Step 2: Run `pytest tests/test_w15_evidence_pack.py -q`** and confirm missing-builder/validator failures.
- [x] **Step 3: Implement the evidence schema, gate registry, and deterministic builder**; omit sensitive values and hash referenced evidence content without embedding it.
- [x] **Step 4: Implement fail-closed validation**; no gate may be inferred as passed from a workflow definition, local test, synthetic benchmark, or absent evidence.
- [ ] **Step 5: Add safe audit helpers** that read branch-rule/evidence metadata where available and report only observed state; helper output may not mutate GitHub settings or external archives. Effective branch-rule readback is unavailable from this local workspace.
- [x] **Step 6: Add `make evidence-pack` and `make readiness-check` targets** plus release artifact upload with exact source SHA and checksums.
- [x] **Step 7: Run evidence tests** with `pytest tests/test_w15_evidence_pack.py -q`; validate that a complete repository-only fixture remains `ready=false` while owner/deployment evidence is missing.
- [x] **Step 8: Commit** as `feat: add fail-closed W15 evidence tooling` (`7a667a3`).

### Task 7: Quality evaluation, operations, privacy and governance documentation

**Files:**
- Modify: `src/tinlance_web_intelligence/evaluation/benchmark.py`
- Modify: `benchmarks/twi/v1/cases.json`
- Modify: `benchmarks/twi/v1/sample_results.json`
- Modify: `scripts/evaluate_twi.py`
- Modify: `docs/evaluation/twi-benchmark.md`
- Modify: `docs/security/threat-model.md`
- Modify: `docs/security/w9-adversarial-validation.md`
- Modify: `docs/operations/w10-observability-sre.md`
- Modify: `docs/operations/private-beta-readiness.md`
- Modify: `docs/operations/incident-response.md`
- Modify: `docs/operations/deployment.md`
- Modify: `docs/roadmap/phases.md`
- Modify: `docs/roadmap/acceptance-criteria.md`
- Modify: W7 audit documents to retain current release evidence and remaining external gates.
- Test: `tests/test_evaluation.py`
- Test: `tests/test_backup_scripts.py`

**Interfaces:**
- Offline benchmark cases remain deterministic and distinguish synthetic results from live quality evidence; no unapproved pass thresholds are added.
- Document owner, evidence source, retention, alert, rollback, support, and escalation fields explicitly; unknown values remain `not_evidenced`.

- [x] **Step 1: Add offline regression cases** for private redirect rejection, tenant scope denial, and monitor baseline capture failure. These cases are explicitly synthetic; extraction instability and consumer drift remain covered by dedicated tests instead of evaluator metrics.
- [x] **Step 2: Run `pytest tests/test_evaluation.py -q` and `python scripts/evaluate_twi.py`**; report hashes and ordering are deterministic, with synthetic cases labelled.
- [x] **Step 3: Update threat and W9 docs** with monitor URL/privacy, baseline concurrency, idempotency, and trace privacy threats plus test references.
- [x] **Step 4: Update W10/runbook/private-beta docs** with tracing state, backup/restore and rollback evidence fields, monitor pause/resume/delete semantics, and explicit external owner gates.
- [ ] **Step 5: Reconcile W7–W15 roadmap, acceptance criteria, and audit findings** against implemented tests and exact-SHA GitHub evidence; local audit edits are preserved, but GitHub branch-rule/CI readback is unavailable.
- [x] **Step 6: Run documentation validators and focused tests**; no generated secrets/PII or deployment approval claims were added.
- [ ] **Step 7: Commit** as `docs: define W15 operations and evidence requirements`.

### Task 8: CI, release checks, full verification, and final forensic audit

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `.github/workflows/release.yml`
- Modify: `Makefile`
- Modify: `scripts/verify_release.py`
- Modify: `scripts/verify_staging.py`
- Modify: `README.md`
- Test: `tests/test_staging_smoke.py`
- Test: `tests/test_provenance.py`
- Test: `tests/test_config.py`

**Interfaces:**
- `make check` includes unit/integration tests, lint, strict typing, dependency/security checks, migration sync, shell validation, consumer contract validation, deterministic evaluation, and evidence-pack structural checks.
- Release evidence is bound to the exact candidate SHA and existing artifact provenance verification; readiness remains false until required external evidence is present.

- [x] **Step 1: Write CI/config/release tests** for migration, pinned contract, evidence checks, and fail-closed readiness behavior; retain the required Python 3.12/3.13 CI matrix.
- [x] **Step 2: Extend CI and `make check`** to run the new checks without weakening existing security, reproducibility, provenance, container, or isolation gates.
- [ ] **Step 3: Extend staging/release probes** for monitor health and telemetry readiness using read-only probes; the existing probes do not yet validate monitor/trace readiness.
- [x] **Step 4: Run local focused verification** on Python 3.12; 199 tests passed, Ruff/mypy/Bandit/migration sync/evaluation and package build passed. Compose validation was unavailable because Docker is absent.
- [ ] **Step 5: Run GitHub CI on the branch and exact final revision**; not run from this workspace, so remote jobs and attached provenance remain `not_evidenced`.
- [x] **Step 6: Conduct final forensic review** against repository tests, local scans, migration copies, privacy boundaries, and evidence pack. PostgreSQL/branch-rule/deployment checks remain external.
- [ ] **Step 7: Produce final readiness report** with repository checks by exact revision, evidence pack digest, and each unavailable external gate marked `not_evidenced`.
- [ ] **Step 8: Commit** as `ci: enforce W15 verification gates`.

## External completion gates

The repository can provide code, tests, validators, templates, and evidence references. Marking a real beta/GA candidate ready additionally requires effective branch protection read-back, exact consumer revisions/approvals, deployment secrets/network/roles/TLS, live security/load/restore/alert evidence, privacy/retention and threshold owners, on-call/support ownership, durable evidence retention, accepted risks, and explicit authorized release approval. Keep each absent item `not_evidenced`.
