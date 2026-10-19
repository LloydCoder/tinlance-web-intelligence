# W15-C — Hard-Job Benchmark and Regression Qualification

**Status:** implementation in progress. The checked-in cases are synthetic contract fixtures; they are not live production-quality evidence.

## Objective

Extend the existing offline benchmark without creating a second benchmark authority. The evaluator must cover difficult acquisition outcomes and expose deterministic, inspectable per-case and aggregate metrics. It must never turn synthetic data into a live-quality claim or imply factual truth from lexical grounding.

## Hard-case matrix

Version the dataset and sample observations together. Each case records a stable ID, challenge class, support status, expected completion status, expected failure classification, expected URL/domain/phrase evidence, freshness limit, and evidence mode (synthetic or live).

Required classes:
- JavaScript-heavy/hydration-dependent pages.
- Pagination and duplicate-page handling.
- Conflicting source observations.
- Transient failure with recovery/retry.
- Anti-bot challenge or access-denied outcome.
- Unsupported content type or unsupported acquisition path.
- Preserve the existing stale-evidence, unsupported-claim, redirect-SSRF, tenant-scope-denial, and capture-failure cases.

## Result and metric contract

Each observation includes evidence records and claims plus completion_status, failure_mode, latency_ms, resource_bytes, request_count, retry_count, and evidence_mode. Resource/latency fields are non-negative bounded integers; request count is positive and retry count is bounded.

The report includes:
- Existing retrieval recall, source-diversity coverage, extraction coverage, citation-grounding heuristic, freshness rate, and exact failure-classification agreement.
- Outcome-contract correctness: expected completion status and expected failure classification both match. This is an observed contract check, not factual correctness.
- Evidence-quality composite: macro mean of the available retrieval, diversity, extraction, grounding, and freshness components, with undefined components excluded and the formula documented.
- Mean and p95 latency, mean resource bytes, mean request count, mean retries, and per-case measurements.
- Counts by challenge class, completion status, failure class, and evidence mode.
- Dataset/result SHA-256, source commit SHA when available, deterministic report SHA-256, and qualification state.

## Qualification and thresholds

- A full 40-character source revision is required for a source-bound report; local runs without it remain not_evidenced.
- benchmarks/twi/v1/thresholds.json is the only qualification threshold registry. No numeric thresholds are pre-approved in this phase. Until an authorized owner, approval reference, and numeric thresholds are recorded, qualification must remain not_evidenced, even if CI passes.
- When approved thresholds exist, the evaluator validates the schema and evaluates the explicitly configured metrics without hiding per-case failures. Threshold approval and evidence are separate from CI.
- Every report identifies all-synthetic datasets as synthetic and must not describe them as live quality.
- Report output must be deterministic for identical dataset/result bytes, fixed evaluation time, source revision, and threshold registry.

## Security and boundaries

- Offline evaluator; no network access.
- Never emit raw source URLs in JSON/Markdown reports.
- Preserve the boundary that provenance and lexical overlap do not establish truth, authority, safety, completeness, or entailment.
- Remain separate from FAS-Bench and reuse benchmarks/twi/v1/ rather than building a parallel framework.

## Acceptance evidence

1. Strict validation for all dataset/result fields, enum values, IDs, timestamps, URLs, and resource bounds.
2. Unit tests for each hard case, unknown/missing fields, duplicate IDs, unsupported schema, invalid classifications, excessive resource values, and missing source revision.
3. Deterministic report bytes/hash and a validator that recomputes the report digest.
4. Thresholds fail closed while unapproved; no release threshold is invented.
5. Python 3.12/3.13 lint, typing, security, unit/contract tests, reproducible release artifact, and browser-isolation workflow green on exact PR head.
6. Post-merge main CI green before W15-D begins.
