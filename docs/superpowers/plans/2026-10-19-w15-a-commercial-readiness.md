# W15-A Implementation Plan

This plan is sequential and evidence-gated. Do not mark W15-A complete based on documentation, scaffolding, or green CI alone.

- [x] A1 — Inspect existing APIs, persistence abstractions, verified principal model, job/monitor entry points, and current tests.
- [x] A2 — Implement versioned plan and entitlement primitives; unknown plans/features fail closed.
- [x] A3 — Implement append-only, tenant-scoped, idempotent usage persistence with SQLite/PostgreSQL parity.
- [x] A4 — Enforce quotas atomically at operation boundaries, including concurrent reservations and rollback on failed submission.
- [x] A5 — Add provider-neutral signed event ingestion, replay protection, event ordering strategy, and reconciliation classifications; do not select a payment provider without approval.
- [x] A6 — Add authorized usage/quota reads and privacy-safe exports.
- [x] A7 — Add adversarial tests: tenant spoofing/isolation, duplicate/reordered events, idempotency conflict, concurrent quota race, failure recovery, and reconciliation mismatches.
- [ ] A8 — Run focused tests, Ruff, mypy, full Python 3.12/3.13 CI; audit the exact PR head and fix all findings.
- [ ] A9 — Merge only when required checks are green; verify post-merge CI and record the exact evidence.
- [ ] A10 — Write a forensic closeout with completed requirements, test evidence, known external gates, and explicit residual risks before W15-B begins.

## Blocking product decisions

- Billing provider and the source of truth for payment/invoice lifecycle.
- Approved plan identifiers, features, quotas, prices, currencies, and trial/overage behavior.
- Whether entitlement state is mirrored from Platform or owned by a designated billing adapter. Platform identity/policy authority must not be duplicated.


## Implementation evidence (W15-A working branch)

- Entitlement primitives and fail-closed decisions: `src/tinlance_web_intelligence/commercial/entitlements.py`, `tests/test_commercial_entitlements.py`.
- Atomic operation-boundary reservation and retry recovery: `src/tinlance_web_intelligence/api/http/routes/jobs.py`, `src/tinlance_web_intelligence/commercial/usage_ledger.py`, `src/tinlance_web_intelligence/persistence/postgres_usage_ledger.py`, `tests/test_api_jobs.py`, and PostgreSQL concurrency tests in `tests/test_postgres_persistence.py`.
- Append-only usage facts and durable billing receipt inbox: `src/tinlance_web_intelligence/commercial/usage_ledger.py`, `src/tinlance_web_intelligence/commercial/billing_inbox.py`, and migration `003_commercial_usage.sql` (source and packaged copies must remain byte-identical).
- Signature verification, replay/conflict handling, conservative event ordering, and reconciliation: `src/tinlance_web_intelligence/commercial/billing_events.py`, `src/tinlance_web_intelligence/commercial/billing_inbox.py`, and `tests/test_billing_events.py`.
- Tenant-scoped quota views and bounded cursor export: `src/tinlance_web_intelligence/api/http/routes/usage.py`, `docs/api/usage-v1.md`, `tests/test_api_usage.py`.

The checkboxes above describe implementation evidence only. A8–A10 remain open until the latest exact head passes all CI jobs, the forensic audit is recorded, the phase PR is merged with required checks green, and post-merge CI passes. Provider-specific webhook wiring and production entitlement resolution remain external integration gates because no billing provider or approved commercial plan catalogue has been selected.
