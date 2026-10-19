# W15-A Implementation Plan

This plan is sequential and evidence-gated. Do not mark W15-A complete based on documentation, scaffolding, or green CI alone.

- [ ] A1 — Inspect existing APIs, persistence abstractions, verified principal model, job/monitor entry points, and current tests.
- [ ] A2 — Implement versioned plan and entitlement primitives; unknown plans/features fail closed.
- [ ] A3 — Implement append-only, tenant-scoped, idempotent usage persistence with SQLite/PostgreSQL parity.
- [ ] A4 — Enforce quotas atomically at operation boundaries, including concurrent reservations and rollback on failed submission.
- [ ] A5 — Add provider-neutral signed event ingestion, replay protection, event ordering strategy, and reconciliation classifications; do not select a payment provider without approval.
- [ ] A6 — Add authorized usage/quota reads and privacy-safe exports.
- [ ] A7 — Add adversarial tests: tenant spoofing/isolation, duplicate/reordered events, idempotency conflict, concurrent quota race, failure recovery, and reconciliation mismatches.
- [ ] A8 — Run focused tests, Ruff, mypy, full Python 3.12/3.13 CI; audit the exact PR head and fix all findings.
- [ ] A9 — Merge only when required checks are green; verify post-merge CI and record the exact evidence.
- [ ] A10 — Write a forensic closeout with completed requirements, test evidence, known external gates, and explicit residual risks before W15-B begins.

## Blocking product decisions

- Billing provider and the source of truth for payment/invoice lifecycle.
- Approved plan identifiers, features, quotas, prices, currencies, and trial/overage behavior.
- Whether entitlement state is mirrored from Platform or owned by a designated billing adapter. Platform identity/policy authority must not be duplicated.
