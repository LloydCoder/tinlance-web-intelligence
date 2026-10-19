# W15-A Commercial Readiness and Billing — Contract

**Status:** Implementation in progress; this document defines the acceptance contract, not a claim of completion.
**Owner:** TWI engineering, with Platform/billing-provider integration owners for external contracts.
**Predecessor:** W1–W15 repository baseline at `8a511f69eacc0d718cbeda38be5edb0705dd36ff`.

## Authority boundaries

- Agent Platform remains the identity, authorization, approval, and governed-execution authority. Tenant and subject are derived exclusively from the verified principal.
- A designated billing system/provider remains authoritative for invoices, payment status, refunds, and tax. TWI must not silently become a payment processor or a second billing ledger.
- TWI owns usage facts for operations it performs and must expose traceable, idempotent usage records. A usage event is not itself proof that a payment settled.
- Agent OS remains the scheduler/task-lifecycle authority. Quota checks must not introduce a competing scheduler.
- No payment provider, commercial plan price, currency, trial policy, tax treatment, or refund policy is assumed by this contract. Those require an approved product/billing decision before provider-specific production wiring.

## Required capabilities

1. **Plan/entitlement contract:** versioned plan definitions, explicit feature grants, hard limits, and a deterministic decision result. Unknown plans/features fail closed.
2. **Quota enforcement:** checks occur at the operation boundary before expensive or externally visible work; concurrency cannot be handled with a process-local counter. Limits distinguish hard rejection from any separately approved soft-warning behavior.
3. **Usage ledger:** append-only operation facts with stable event IDs, tenant-scoped access, bounded dimensions, UTC occurrence time, schema version, and idempotent replay. Caller-provided tenant IDs are never trusted.
4. **Reconciliation:** usage exports/reconciliation compare usage event IDs and quantities against billing-provider records. Missing, duplicate, reversed, or mismatched records are explicit findings, not silently corrected totals.
5. **Lifecycle reliability:** provider events are signature-verified, replay-safe, idempotent, ordered defensively, and recoverable. Billing outages must not accidentally grant access or double-charge customers.
6. **Customer controls:** authorized usage/quota/spend views and bounded notifications; no leakage of another tenant's usage or private source data.
7. **Operational safety:** retries, duplicate delivery, dead-letter/replay, audit trails, privacy-safe logs, and explicit manual-review paths for ambiguous financial states.

## Acceptance gates

- Unit and API tests cover plan-version compatibility, unknown feature denial, boundary conditions, tenant isolation, caller-identity spoofing, idempotency collisions, duplicate/reordered provider events, replay, signature failure, quota race conditions, and billing/usage reconciliation.
- Integration tests use a documented provider sandbox or contract fixture; no live payment is created by tests.
- Quota enforcement is persistent and atomic under concurrent requests; a process-local in-memory counter is insufficient.
- Usage facts are immutable; corrections use compensating events with lineage.
- Reconciliation output is deterministic, versioned, privacy-safe, and has explicit mismatch classifications.
- CI is green on the exact PR head; a phase-specific forensic audit records implementation evidence, test results, known gaps, and external dependencies before W15-B starts.
- External billing authority/provider configuration and commercial policy approval remain `not_evidenced` until supported by source-bound evidence.

## Implementation sequence

A1. Inspect existing API, persistence, principal, job and monitor boundaries; avoid duplicate ledgers.
A2. Add versioned plan/entitlement primitives and fail-closed tests.
A3. Add persistent idempotent usage events and atomic quota reservation at the operation boundary.
A4. Add provider-neutral signed-event ingestion contract and reconciliation interfaces; provider adapter remains blocked until explicitly selected.
A5. Add tenant-scoped usage reads, evidence-safe exports, docs and adversarial tests.
A6. Run focused tests, complete CI, audit the exact PR head, fix all findings, merge only with green checks, and verify post-merge CI.

## Explicit non-claims

A green CI run does not establish live billing, provider settlement, pricing approval, production entitlement configuration, or legal/tax compliance. Those remain external release gates.
