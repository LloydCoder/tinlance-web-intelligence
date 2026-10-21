# Tinlyt Commercial Pricing Policy v1

**Status:** Approved market-facing launch rates; billing enforcement and plan allowances are not yet certified or enabled by this document alone.  
**Product:** Tinlyt (engineering workstream: Tinlance Web Intelligence / TWI)  
**Currency:** USD  
**Decision date:** 2026-10-20

This document records the approved proposed public unit rates and the rules required before charging customers. It is a pricing policy, not evidence that a payment provider, subscription catalogue, production entitlement resolver, invoice ledger, or live billing workflow has been implemented.

## 1. Public unit rates

| Meter | Rate | Unit |
|---|---:|---|
| Agent execution | $0.014 | Per billable agent step |
| Standalone browser execution | $0.002 | Per billable browser minute |
| Search and Fetch | $0 within a bounded free allowance | Allowance size must be configured and cost-validated before paid launch |
| Platform-caused failed work | $0 | Failed work attributable to a Tinlyt service/infrastructure defect is not billable |

The agent-step rate is 12.5% below TinyFish's published $0.016 per-step rate. The standalone browser-minute rate matches TinyFish's published $0.002 per-minute benchmark. Competitor prices are reference points only; they do not establish Tinlyt's cost to serve or margin.

## 2. Billable agent step

A billable agent step is one completed, customer-visible, metered agent operation that:
- belongs to an authorized tenant and an accepted run;
- has a stable run ID and step ID;
- has an operation class and recorded outcome;
- is recorded exactly once in the durable usage ledger; and
- is eligible under the tenant's active entitlement and spend policy.

Internal logs, spans, token events, queue deliveries, orchestration bookkeeping, and unexposed implementation sub-operations are not separately billable steps. A retry caused by a Tinlyt infrastructure fault is not charged. An external website rejection, rate limit, or unavailable source is not automatically a Tinlyt infrastructure fault; billing behavior must follow the published outcome policy and must never misrepresent a failed operation as a successful one.

## 3. Browser-minute meter

A browser minute measures active, billable browser execution time for an explicitly requested standalone browser session. The implementation must define the clock source, rounding rule, idle-time treatment, maximum duration, cancellation cutoff, and treatment of startup/shutdown time before the meter is enabled. Do not round each tiny interval upward independently; aggregate duration per session and apply the published rounding rule once.

If a browser action is already included in a billable agent step, the same work must not be charged again as standalone browser usage unless the customer explicitly selected a separately metered browser session and the product clearly disclosed that distinction before execution.

## 4. Failure, retry, cancellation, and refunds

- **Platform-caused failure:** Do not charge the failed work attributable to a Tinlyt defect or infrastructure failure. Reverse any provisional usage reservation/charge through an auditable compensating entry.
- **Retry:** Deduplicate repeated delivery and retries using stable idempotency keys. A retry does not create a second charge for the same logical step.
- **Partial completion:** Charge only completed billable steps that are represented in the usage ledger; do not bill planned, queued, or never-started work.
- **External-source failure:** A remote website's own rejection or outage is distinct from Tinlyt infrastructure failure. Record the outcome and apply only a clearly documented policy; never label the work successful if it failed.
- **Cancellation:** Stop new billable work when cancellation takes effect. Charge only previously completed billable work that was disclosed to the customer.
- **Correction:** Usage corrections and refunds are append-only compensating records. Never silently edit or delete a committed usage fact.

The usage API reports usage facts and quotas; it is not an invoice, payment-settlement, tax, or refund-status API.

## 5. Subscription plans

The recorded monthly subscription price points are:

| Plan | Monthly price |
|---|---:|
| Free | $0 |
| Starter | $29 |
| Pro | $99 |
| Business | $299 |
| Scale | $799 |
| Enterprise | Custom contract |

These are monthly headline prices. The exact included agent-step allowance, browser-minute allowance, Search/Fetch limits, concurrency, retention, support commitments, and overage entitlement per plan are not defined by this document. They must be expressed in a versioned plan catalogue and backed by the approved billing/entitlement integration before customers are charged. Do not infer allowances from the price or advertise unlimited usage.

The $0.014 agent-step rate and $0.002 standalone browser-minute rate are the standard proposed overage rates once a versioned plan catalogue explicitly enables overages. No overage may occur silently or bypass tenant budget and spend limits. Enterprise rates and contractual commitments require a signed customer-specific agreement.

## 6. Required billing controls

Before paid production launch, implementation and tests must demonstrate:

1. An approved billing boundary and provider-neutral, versioned plan catalogue.
2. Fail-closed tenant entitlement resolution from the verified Platform principal.
3. Durable atomic quota/spend reservation before consequential execution.
4. Append-only usage facts with unique event IDs and idempotent commit semantics.
5. Exact-once logical charging under worker retries, queue redelivery, concurrent requests, and recovery.
6. Meter separation for agent steps and standalone browser minutes, including a no-double-charge invariant.
7. Auditable compensating entries for platform-caused failures and corrections.
8. Hard tenant budgets, usage caps, rate limits, and clear out-of-quota behavior.
9. Tests for rounding, concurrency, partial completion, cancellation, failure attribution, duplicate events, refunds, and plan-version changes.
10. Customer-visible usage and billing disclosures consistent with the actual ledger and provider integration.
11. Cost-to-serve measurements on representative workloads. A 70% gross-margin target implies average direct cost no greater than $0.0042 per $0.014 agent step and $0.0006 per $0.002 browser minute; these are target ceilings, not measured Tinlyt costs.
12. A verified provider integration for payment, invoicing, tax, subscription lifecycle, and customer support where applicable.

Until these gates pass, treat the rates as the approved pricing decision for product design and listing preparation, not as authorization to collect payment or represent production billing as operational.

## 7. Authority and non-goals

- Agent Platform remains authoritative for identity, authorization, policy, approvals, budgets, secrets, audit, and governed execution.
- TWI owns acquisition operations and usage facts; its usage API does not replace the billing provider's ledger.
- A provider-neutral entitlement primitive is not a customer subscription or payment contract.
- Marketplace listing approval does not establish that billing is enabled or that marketplace platforms collect or remit Tinlyt subscription revenue.

## 8. Change control

Any change to unit rates, billable-unit definitions, free allowances, rounding, failure policy, or plan allowances requires a versioned policy change, tests, and coordinated updates to customer-facing pricing, API contracts, entitlement configuration, and billing implementation.
