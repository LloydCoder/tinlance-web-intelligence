# W15 Enterprise Readiness Design

**Status:** Design approved; repository implementation advanced in isolated branch `codex/w15-enterprise-readiness`. Repository tests pass locally; external CI/deployment/governance evidence is still required.
**Date:** 2026-10-19
**Repository baseline:** `d411706b31aedc4ac20b788d272b5b72f1af4449`

## Goal

Advance Tinlance Web Intelligence through the repository-level requirements for W7–W15 with verifiable engineering, security, release, evidence, operations, and evaluation controls. Keep deployment-specific release approval separate: a green repository cannot certify an unobserved production environment.

## Existing state and constraints

- W1–W6 foundations are implemented and CI-covered. W7 has pinned dependency and image scans, reproducible release artifacts, SBOM and provenance verification. W8 has staging Compose topology. W9 has adversarial regression tests. W10 has API and durable queue/outbox metrics. W11 has provenance, freshness, evidence-pack integrity, and job-data retention foundations. W12 has an offline deterministic benchmark.
- Remaining recorded gaps include enforceable branch governance, durable retention/distribution of release evidence, deployment-side validation, distributed traces and broader worker/browser telemetry, approved data-retention and URL privacy policy, representative quality baselines, monitoring/change intelligence, automated consumer-version checks, and GA evidence/operations.
- The service must preserve the authority boundaries in `docs/architecture/component-boundaries.md`: Agent Platform owns identity, policy, authorization and approvals; Agent OS owns task lifecycle and recurrence; TWI owns acquisition, extraction, artifacts, provenance and change analysis; World Intelligence owns canonical world state and truth judgments; TSIC validates ecosystem conformance.
- Do not fabricate live results, quality thresholds, SLO acceptance, risk acceptance, cloud deployments, branch-rule settings, or GA approval.

## Architecture

### Ownership and data flow

1. The Agent OS schedules recurring work and invokes TWI through Platform-authorized operations. TWI will not run a second scheduler.
2. Agent Platform remains the only identity and policy authority. TWI derives tenant and subject from its verified principal and ignores caller-supplied identity fields.
3. TWI stores tenant-scoped monitor definitions and durable run jobs. The first successful run establishes a baseline; later runs compare deterministic normalized extracted text and emit bounded change metadata. TWI reports observed changes and candidate evidence only; it does not assert truth or mutate canonical World Intelligence state.
4. World Intelligence export remains an explicit, authorized, idempotent operation through the existing outbox.
5. W14 contract checks bind to recorded Platform, World Intelligence and TSIC consumer revisions. Changes to those consumers require an explicit snapshot refresh and compatibility review.

### Monitoring API and lifecycle

Add versioned operations consistent with existing `/v1` job patterns:

- `POST /v1/monitors` creates a monitor definition. It requires an idempotency key, validates the target through the existing safe URL policy, derives tenant/subject from the verified principal, and stores a bounded extraction/change policy.
- `GET /v1/monitors/{monitor_id}` reads only a monitor visible to the caller's tenant; subject-level access follows the existing administrative-scope pattern.
- `POST /v1/monitors/{monitor_id}/runs` enqueues a durable, idempotent run and returns `202 Accepted` with the existing job contract. Agent OS controls when this operation is invoked.
- `POST /v1/monitors/{monitor_id}/pause` and `/resume` stop or allow future runs. Pause does not revoke an active worker lease. A separately scoped delete operation redacts monitor state according to the approved retention policy.
- `GET /v1/monitors/{monitor_id}/runs/{job_id}` reuses tenant-scoped job reads and exposes the deterministic change result and artifact references.

The first successful capture initializes the baseline and reports `baseline_established`. Later captures compare normalized extracted text digests. Results include prior/current digests, observation times, changed/unchanged status and bounded counts; they do not contain full page text or claim semantic entailment. Failed or stale runs do not advance the successful baseline. Database transactions or optimistic version checks prevent concurrent runs from overwriting a newer baseline. Existing PostgreSQL `SKIP LOCKED` leases and idempotency rules remain authoritative for jobs.

Monitor storage uses PostgreSQL in production and the existing SQLite test/development path. Add synchronized SQL migration copies and rollback/recovery behavior. Keep the exact fetch target only where execution requires it; minimize or redact URL material in derived results, logs, metrics, traces and evidence packages. Never accept URL userinfo. Preserve compatibility for existing evidence consumers and document any new schema fields as additive/versioned.

### Telemetry and trace propagation

- Use W3C Trace Context (`traceparent`) across API requests, durable jobs, worker execution, browser broker calls, and World Intelligence export. Persist only validated trace context needed to continue a trace; do not propagate baggage by default.
- Add OpenTelemetry spans with bounded attributes such as operation, component, outcome and error class. Exclude raw URLs, page content, tenant/subject identifiers, tokens, request IDs and arbitrary user fields.
- If no exporter endpoint is configured, tracing remains non-exporting and does not block service behavior. Production deployment must configure an approved collector separately.
- Add bounded browser, provider and worker counters/durations, retaining the existing Prometheus no-high-cardinality rules.

### Consumer contracts and evidence pack

- Maintain a machine-readable compatibility matrix containing consumer name, repository, exact revision, contract/schema version, and evidence link. Validate the TWI tool catalog and schemas against pinned consumer fixtures in CI; test positive requests and negative scope/tenant cases.
- Add a deterministic W15 evidence-pack manifest and validator. Each required gate uses exactly `pass`, `fail`, or `not_evidenced`, and records owner, timestamp, source revision, evidence reference and SHA-256 digest. The validator rejects missing/expired evidence, mismatched revisions, invalid digests, unresolved required findings, and attempts to mark W15 complete while any required gate is not `pass`.
- The pack omits credentials, raw page content, raw URLs with query values, tenant IDs and personal data. The tooling reports presence and integrity; durable storage and immutable retention are configured externally.

## Security and privacy requirements

- Reuse connection-time DNS/IP validation, redirect revalidation, response/time limits, browser proxy-only egress, Chromium sandboxing and current tenant authorization.
- Add adversarial tests for malformed/blocked URLs, redirect/DNS rebinding paths, cross-tenant monitor and artifact reads, scope denial, idempotency collisions, concurrent baseline updates, replay, cancellation, stale/future results, and exporter outages.
- Do not emit sensitive values in logs, metrics, traces, benchmark reports, or evidence-pack metadata. Preserve tenant-scoped artifact integrity checks.
- Retention remains dry-run by default. Destructive cleanup requires the separate least-privilege maintenance DSN and explicit confirmation. Retention intervals, URL minimization acceptance and managed-key rotation require an authorized owner and target-environment evidence.
- No automatic web content action, scheduled execution, or canonical World Intelligence mutation is introduced by a detected change.

## Workstream outcomes

| Gate | Repository outcome | Owner/deployment evidence still required |
|---|---|---|
| W7 | Keep pinned dependency/image audits, reproducible builds, SBOM, checksum and independent provenance checks. Add deterministic evidence indexing/validation and a read-only governance audit helper where useful. | Apply/read back effective branch rules; archive scan and release evidence beyond workflow retention; select durable customer distribution and risk owner. |
| W8 | Keep validated production-like topology and read-only staging probes; add config/schema checks for new components. | Approved cloud/workspace, real network controls, secrets and rotation, database roles/TLS, full Platform→TWI→World Intelligence journey, restore rehearsal. |
| W9 | Extend automated adversarial regression coverage for monitors, trace privacy and multi-tenant authorization. | Live security assessment against the exact deployed candidate. |
| W10 | Add cross-process traces and browser/provider/worker outcome and latency metrics, plus provider-neutral collector/alert examples and load/failure harnesses. | Owner-approved SLOs, actual collector/paging route, measured capacity, alert delivery, on-call and witnessed rollback. |
| W11 | Enforce data-minimization behavior, tenant-safe monitor storage, deletion semantics and integrity checks in code and tests. | Approve retention/privacy schedule, verify managed encryption/key rotation and deployed role isolation, archive deletion/recovery evidence. |
| W12 | Expand deterministic, offline cases from documented incident classes; preserve hashed datasets and stable reports. Do not claim synthetic fixtures are live quality results. | Collect privacy-reviewed real observations, set human-approved task thresholds and record live regression baselines. |
| W13 | Implement durable monitor definitions/runs, deterministic baseline/change detection, idempotency, pause/resume, bounded retries, retention and schema/Platform contracts. | Configure Agent OS recurrence and perform real-network monitoring/alert validation. |
| W14 | Implement exact-revision consumer compatibility fixtures, schema checks, and negative tenant/scope tests; preserve single authority boundaries. | Confirm target consumer versions, Platform registration/policy and TSIC conformance with owning repositories. |
| W15 | Provide an evidence-pack generator/validator, threat/risk/runbook/capacity templates, release checks and a fail-closed readiness decision. | Supply exact deployment artifacts, live security/load/restore/alert evidence, named support/on-call ownership, accepted risks, and explicit authorized GA approval. |

## Verification and release gates

- Run focused tests for every changed behavior and the full `make check` suite on Python 3.12 and 3.13, including PostgreSQL integration, migration synchronization, shell validation, offline benchmark, browser runtime and isolation checks.
- Verify Compose topology, all container scans, dependency audit, package wheel/sdist, reproducibility, SBOM, checksums and provenance on the exact candidate SHA. Confirm GitHub CI on PR head and merged commit.
- Add a migration test for fresh install, upgrade from current schema, concurrent monitor runs, recovery after failed capture, and tenant isolation.
- Audit the evidence pack against each row in `docs/operations/private-beta-readiness.md`; retain every deployment or owner gate as `not_evidenced` until its exact evidence is supplied.
- Do not mark W7–W15 or private beta/GA complete based only on local tests, a workflow file, synthetic benchmark data, or this design.

## Non-goals and external prerequisites

- This design does not create another MCP server, identity/policy authority, scheduler, truth classifier, or automatic source-action workflow.
- Cloud-specific IaC, secret-manager selection, branch rules, actual evidence archival, production access, cross-repository mutations, live web measurements, on-call staffing, risk acceptance and release/GA approval are out of scope until an authorized target and credentials are provided.
- The local Python 3.14 installation previously reported `Failed to find real location`; implementation verification must use the supported 3.12/3.13 CI matrix unless the local toolchain is repaired.
