# Private-beta readiness

**Current release state: NOT CERTIFIED.** The repository implementation is merged and CI-verified, but every checklist item below requires evidence from the target deployment. Do not infer private-beta readiness from green repository CI alone.
## Checklist

Private beta is a deployment-specific decision, not a repository label. Every item must link to evidence for the exact release candidate and environment.

## Product and integration

- [ ] W1–W5 gates are complete and their evidence is reconciled with main.
- [ ] Platform-owned MCP catalog registration and operation-level policy are verified in the Platform repository.
- [ ] World Intelligence ingestion contract and TSIC conformance results are verified against the intended consumer versions.
- [ ] No TWI endpoint or worker creates a parallel identity, approval, audit, or execution authority.

## Security

- [ ] Production PostgreSQL uses TLS certificate and hostname verification (sslmode=verify-full).
- [ ] Schema is migrated by a separate, least-privilege DDL role before startup; runtime credentials cannot create or alter tables.
- [ ] Production secrets are injected from an approved secret manager and rotation has been exercised.
- [ ] API, workers, browser broker, browser worker, and egress proxy have least-privilege network policies.
- [ ] SSRF, DNS rebinding, redirect, prompt-injection, cross-tenant and unauthorized-operation tests pass.
- [ ] Dependency, static security, image, and vulnerability scans have no unresolved critical/high findings unless explicitly risk-accepted by the authorized owner.
- [ ] Threat model and residual-risk register are current.

## Reliability and operations

- [ ] Raw artifact bytes and capture metadata are stored durably in tenant-scoped PostgreSQL tables; reads verify SHA-256 integrity and access is tenant-isolated.
- [ ] Artifact retention interval and maintenance-role permissions are configured; dry-run results are reviewed and destructive runs require explicit confirmation.
- [ ] PostgreSQL multi-worker claim tests pass; retries, lease expiry, cancellation and idempotency are verified.
- [ ] Metrics, traces, structured logs, alert thresholds and on-call ownership are configured in the target environment.
- [ ] Backup encryption, retention, alerting and a witnessed restore drill are verified.
- [ ] Capacity, load, rate limits, provider quotas and failure-mode tests meet agreed SLOs.
- [ ] Incident response, rollback, recovery and support runbooks are exercised.
- [ ] API and browser egress restrictions are verified in the actual deployment environment.

## Release decision

- [ ] CI is green on the exact PR head and post-merge main commit.
- [ ] Release artifacts are reproducible, scanned and traceable to a commit.
- [ ] All audit evidence has an owner and timestamp.
- [ ] Authorized owner explicitly approves private beta.

If a box is unchecked or lacks evidence, private beta remains NOT CERTIFIED. Passing repository CI alone is not production-deployment evidence.

## W15 monitor controls

- [ ] Confirm Agent OS owns the monitor recurrence policy and has approved run cadence and budget.
- [ ] Verify monitor creation, run idempotency, pause/drain, tenant separation and deletion against the target deployment.
- [ ] Approve URL/query retention and monitor-result retention with a named privacy owner.
- [ ] Verify PostgreSQL migration 002, backup/restore, active-worker deletion behavior and target egress.
- [ ] Bind Platform, World Intelligence and TSIC contracts to exact reviewed consumer revisions.
- [ ] Confirm collector, paging route, on-call owner and a witnessed alert/rollback exercise.

The current Platform main revision `c5a080c1fb4df68e45070f8cddfc30bf81edd7bb` registers all six monitor operations and evidence export; its CI, security, supply-chain, and certification workflows pass. The TWI consumer snapshot and W15 consumer-approval gate are refreshed to that immutable revision. The current TWI main commit `02403b505622d03bb96ee87fb59518cbd26342d2` passed all four CI jobs in [run 41608705421](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/41608705421): Python quality/tests on 3.12 and 3.13, browser container isolation, and reproducible release artifact validation. The exact-run evidence record is `docs/evidence/2026-11-03-main-02403b505622d03bb96ee87fb59518cbd26342d2.json`. This is repository CI evidence only; it does not attest to a live deployment, authenticated API journey, privacy approval, witnessed recovery from a real encrypted backup, TSIC conformance, SLO/on-call, or GA approval. The previously recorded `/` and `/app` route smoke observation is historical and must be repeated against the target deployment before beta. The W15 pack still reports `ready=false`: branch governance, deployed API/identity, real encrypted-backup recovery, TSIC conformance, SLO/on-call, privacy/retention, and live-quality/GA gates remain `not_evidenced`.
