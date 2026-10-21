# W15-A commercial readiness closeout — repository evidence

**Status:** Repository implementation and CI-verified; live billing is **not enabled**.  
**Current verified main revision:** `a407b211773e32a71a8cebcae9b9b2177fd5af5c`  
**CI evidence:** [Post-merge CI run 39573798125](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39573798125)

## Implemented repository components

- Versioned, fail-closed plan entitlement decisions: `src/tinlance_web_intelligence/commercial/entitlements.py`.
- Append-only usage facts, idempotency keys, atomic quota reservations, and release/commit lifecycle for local development/test storage: `src/tinlance_web_intelligence/commercial/usage_ledger.py`.
- PostgreSQL-backed usage persistence and migration parity: `src/tinlance_web_intelligence/persistence/postgres_usage_ledger.py`, `src/tinlance_web_intelligence/persistence/migrations/003_commercial_usage.sql`, and `db/migrations/003_commercial_usage.sql`.
- HMAC-SHA256 signed-event verification over timestamp plus raw request bytes, bounded payloads, timestamp tolerance, duplicate-JSON-key rejection, and payload digesting: `src/tinlance_web_intelligence/commercial/billing_events.py`.
- Durable idempotent event receipt inbox with provider/event uniqueness and conflicting-payload detection: `src/tinlance_web_intelligence/commercial/billing_inbox.py`.
- Deterministic usage-vs-billing reconciliation findings: `reconcile_usage` in `billing_events.py`.
- Principal-scoped usage API with bounded pagination and privacy-minimized output: `src/tinlance_web_intelligence/api/http/routes/usage.py`.
- Focused tests are maintained in `tests/test_commercial_entitlements.py`, `tests/test_commercial_usage_ledger.py`, `tests/test_commercial_usage_migration.py`, `tests/test_billing_events.py`, and `tests/test_api_usage.py`.

## What this does not prove

This repository implements a billing foundation, not a live payment product. No provider-specific checkout/subscription adapter, production webhook route wired to a merchant account, financial ledger of invoices/refunds/fees/settlements, or live reconciliation against a payment processor is certified by this closeout. A generic HMAC event verifier does not establish compatibility with a provider's exact signature scheme. SQLite implementations are for local/test use; deployed multi-replica usage and billing receipts must use PostgreSQL.

The product/provider decision and approved commercial catalogue must be explicit before enabling checkout. The recorded architecture direction is provider-neutral domain logic with Polar as the proposed global SaaS Merchant of Record, Paystack as a Nigerian payment rail, and Grey as a separate treasury/settlement option—not a checkout substitute. These choices still require current provider API review, account approval, contract tests, and owner sign-off before adapters or production routing can be enabled.

## Required next gates

1. Select and approve the initial checkout/subscription provider and legal merchant-of-record model.
2. Implement its exact signature verification, checkout/customer/subscription lifecycle, event mapping, refund/cancellation handling, and provider API contract tests.
3. Persist canonical customer, organisation, product/price version, subscription, invoice, payment, refund, entitlement, and webhook-event records in the designated commerce boundary; avoid making TWI the competing financial authority if Tinlance Commerce owns these models.
4. Add sandbox tests for checkout → signed webhook → immutable receipt → entitlement update → usage reservation/settlement → invoice and settlement reconciliation.
5. Verify idempotency, duplicate/reordered events, signature rotation, retries/dead letters, provider outage behavior, integer money arithmetic, spending limits, refunds, chargebacks, and renewal failures.
6. Keep live charges disabled until authorized merchant credentials, legal/tax disclosures, settlement/reconciliation evidence, and release approval exist.

## Evidence interpretation

The cited CI run is evidence that the configured repository workflow passed on the exact main revision. It is not live-provider, production deployment, financial reconciliation, or private-beta/GA certification. Private beta remains **NOT CERTIFIED** until the external gates in `docs/readiness/w15-gates.json` and `docs/operations/private-beta-readiness.md` have evidence from the intended target environment.
