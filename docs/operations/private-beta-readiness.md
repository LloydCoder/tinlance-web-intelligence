# Private-beta readiness checklist

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
