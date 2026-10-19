# TWI reproducible hard-job evaluation benchmark

## Purpose and authority boundaries

The evaluator scores recorded observations offline; it performs no network access. It is intentionally separate from FAS-Bench and does not create a second identity, policy, approval, scheduler, evidence, or World Intelligence authority. It measures observable acquisition and evidence properties. It does not establish factual truth, source authority, safety, completeness, or semantic entailment.

All checked-in observations are synthetic contract fixtures. They exercise the evaluator and are not live production-quality evidence.

## Run

From the repository root, use a fixed evaluation timestamp:

```bash
python scripts/evaluate_twi.py \
  --dataset benchmarks/twi/v1/cases.json \
  --results benchmarks/twi/v1/sample_results.json \
  --thresholds benchmarks/twi/v1/thresholds.json \
  --now 2026-10-19T12:00:00Z \
  --json-out /tmp/twi-evaluation.json \
  --markdown-out /tmp/twi-evaluation.md
```

The fixed `--now` prevents wall-clock drift. Reports hash the exact dataset, results, and threshold-registry bytes and include a deterministic report digest and, when supplied, a full source commit SHA. Identical inputs, fixed time, source revision, and threshold registry produce identical JSON report content. The CLI does not emit source URLs in reports.

## Hard-job coverage

The versioned dataset in `benchmarks/twi/v1/cases.json` covers baseline retrieval, stale evidence, unsupported claims, redirect/SSRF blocking, tenant-scope denial, capture failure, JavaScript-heavy/hydration-dependent content, pagination with duplicate retrieval, conflicting source observations, transient failure recovery, anti-bot challenges, and unsupported content types. Each case declares challenge class, support status, expected completion outcome, expected failure classification, expected source/domain/phrase evidence, freshness bound, evidence mode, and duplicate-retrieval allowance.

The paired results file records retrieved evidence and claims plus completion status, failure mode, latency, resource bytes, request count, retry count, and evidence mode. Dataset and results use strict versioned contracts; malformed or mismatched case IDs, invalid timestamps, URLs with userinfo, unknown enums, and out-of-range measurements are rejected.

## Metrics

- **Retrieval recall:** expected normalized URLs present in retrieved observations divided by expected URLs.
- **Source-diversity coverage:** expected hostnames represented in retrieved observations divided by expected hostnames.
- **Extraction coverage:** expected phrases present in extracted title/text divided by expected phrases.
- **Citation-grounding rate:** claims whose cited URLs are present and whose non-stopword tokens have at least 50% lexical overlap with one cited source. This is a heuristic, not semantic entailment.
- **Freshness rate:** retrieved items within the case's explicit maximum age and five-minute future-clock-skew allowance. Cases with no retrieved evidence have no freshness score.
- **Failure-calibration accuracy:** exact agreement between expected and observed failure classification. This is classification agreement, not probabilistic calibration.
- **Outcome-contract correctness:** expected completion status and failure classification match, and duplicate retrievals remain within the case's explicit allowance.
- **Evidence-quality score:** macro mean of retrieval recall, source-diversity coverage, extraction coverage, and available citation-grounding/freshness metrics. Undefined components are excluded; this score is not truth.
- **Operational measurements:** mean and nearest-rank p95 latency, mean resource bytes, mean requests, mean retries, and per-case measurements.

Aggregate quality metrics are macro-averaged by case; undefined metrics are excluded. Reports retain per-case results and counts by challenge class, completion status, failure mode, support status, and evidence mode so aggregate values cannot hide individual failures.

## Qualification and threshold governance

`benchmarks/twi/v1/thresholds.json` is the only qualification threshold registry. It is deliberately unapproved and contains no numeric limits. Until an authorized owner, approval reference, and numeric thresholds are recorded, qualification remains `not_evidenced`. The evaluator validates the registry again at the evaluation boundary; callers cannot bypass owner/reference/schema validation by passing a raw mapping. Qualification requires the exact raw registry bytes, verifies that the supplied SHA-256 matches those bytes, and verifies that any supplied parsed mapping matches the raw registry. A digest string alone cannot qualify a result. A full source revision is required for source-bound qualification, and synthetic or mixed evidence cannot qualify live quality.

No threshold is inferred from the sample results or selected merely to make CI pass. Threshold approval is a separate product/quality governance decision.

## Interpretation and limitations

The sample observations are synthetic. The pagination case intentionally contains a duplicate page to exercise duplicate accounting and outcome-contract scoring. The conflicting-source case records the expected conflict classification; it does not decide which source is true. Synthetic scores must not be interpreted as a production quality baseline.

A green CI run establishes that the implementation passes its automated contract checks on the tested revision; it does not establish live-world quality, external integration approval, production SLOs, or GA authorization. Add cases only with reviewable rationale and expected outcomes; bump the schema version when the contract changes.
