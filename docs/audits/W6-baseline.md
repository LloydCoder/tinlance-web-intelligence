# W6 baseline audit — private-beta and operational readiness

## Initial evidence

- Main commit reviewed: af1aea81fb090c5fd480bf1e617718b9ba1b1ce2.
- Main CI run: https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39159210700 completed successfully on 2026-10-18.
- W1–W4 are recorded as merged in the prior phase ledger, with W4 browser-isolation CI evidence.
- W5 code exists on main, including citation verification, tenant/subject-scoped evidence export, an idempotent outbox, and a World Intelligence delivery worker. The phase ledger and Platform/TSIC consumer registration evidence are inconsistent and must be reconciled before W5 can be certified complete.
- The prior deployment documentation describes SQLite as a single-node store and explicitly gates multi-replica production use on W6.
- The artifact store is documented as process-local and development/test only.

## W6 scope

1. Promote job and evidence-outbox persistence to PostgreSQL with transactional idempotency and SKIP LOCKED leasing; keep schema DDL in an explicit migration job using a distinct production role.
2. Fail closed in production unless a PostgreSQL URL with sslmode=verify-full is configured.
3. Exercise multi-worker claims, idempotency conflicts, tenant isolation, lease ownership and outbox delivery against a real PostgreSQL service in CI.
4. Update deployment, backup/restore, incident response and private-beta runbooks.
5. Verify the full repository, security and consumer integration gates before any private-beta claim.

## Certification rule

This file is a baseline, not a completion certificate. Final disposition must record the exact PR head SHA, required CI run IDs, post-merge main SHA and CI, test/security results, consumer conformance evidence, and unresolved deployment-specific risks. No production deployment or restore drill may be claimed unless independently evidenced.
