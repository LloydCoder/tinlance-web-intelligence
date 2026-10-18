# Incident response runbook

## Severity and containment

- **P0 — credential exposure, cross-tenant access, or unsafe internal-network access:** stop affected acquisition/workers, revoke exposed credentials, preserve audit records, and notify the authorized security owner immediately.
- **P1 — data integrity or widespread service failure:** pause queue consumers, preserve database snapshots and logs, assess idempotency/replay safety, and coordinate recovery.
- **P2 — isolated provider, extraction, or queue degradation:** apply bounded retries or disable the affected provider using configuration; do not weaken destination policy.
- **P3 — documentation or non-production defect:** track through the repository issue process.

## First-response checklist

1. Record UTC start time, affected deployment/version, request or trace IDs, and observed symptoms.
2. Do not copy access tokens, source payloads, secrets, or personal data into tickets.
3. Determine whether the issue affects API, worker, browser sandbox, egress proxy, PostgreSQL, or World Intelligence delivery.
4. If unsafe egress or tenant leakage is suspected, disable the affected capability before collecting further evidence.
5. Preserve least-privilege logs and relevant database evidence; follow retention policy.
6. Restore from a known-good backup only after the incident lead approves the target and recovery plan.
7. Validate health, authorization denials, queue lease recovery, tenant scoping, and outbox replay before reopening traffic.
8. Document root cause, impact, corrective actions, owners, and follow-up tests.

## Non-negotiable controls

Do not bypass Platform policy, disable Chromium sandboxing, allow direct browser egress, log credentials, or manually mark unverified source claims as true to restore service.
