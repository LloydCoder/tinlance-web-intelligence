# W12 intelligence quality and evaluation audit

**Status:** Repository benchmark and CLI are implemented; live evaluation and acceptance gates remain open.

## Implementation

- Versioned dataset: benchmarks/twi/v1/cases.json.
- Deterministic recorded observations: benchmarks/twi/v1/sample_results.json.
- Evaluator: src/tinlance_web_intelligence/evaluation/benchmark.py; CLI: scripts/evaluate_twi.py.
- Metrics: retrieval recall, expected source-domain coverage, extraction phrase coverage, lexical citation-grounding rate, freshness rate, and exact failure-mode agreement.
- Reproducibility: explicit timezone-aware --now, SHA-256 of exact dataset/results bytes, stable JSON and Markdown reports, and no raw source URLs in reports.
- Input guards: schema version and dataset ID, exact case-set match, unique case IDs, absolute HTTP(S) URLs without userinfo, timezone-aware timestamps, and bounded text size.
- Makefile evaluation-check target is included in make check; unit tests validate the CLI outputs and deterministic metric values.

## CI evidence

- W12 benchmark merged through PR [#52](https://github.com/LloydCoder/tinlance-web-intelligence/pull/52), merge commit 75c3e25080f0e5c3b3295ffaf07a57aa1bbbc0c8.
- Exact-head CI run [#682](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39223956382) passed Python 3.12, Python 3.13, isolated browser/egress controls, container vulnerability policy, and reproducible release artifact validation.

## Fixture baseline (methodology check only)

| Metric | Expected sample value |
|---|---:|
| Retrieval recall | 0.833333 |
| Source-diversity coverage | 0.833333 |
| Extraction coverage | 0.666667 |
| Citation-grounding rate | 0.500000 |
| Freshness rate | 0.666667 |
| Failure-calibration accuracy | 1.000000 |

These values characterize three checked-in synthetic observations, not the production service or live web retrieval. The citation-grounding metric is lexical overlap and is not semantic entailment.

## Remaining W12 exit gates

- Collect representative, privacy-reviewed observations from the actual TWI retrieval/extraction pipeline and run the benchmark against them.
- Agree metric thresholds and regression tolerances with the owning team; document why each threshold is suitable for its task.
- Add cases for source diversity failure, malformed/blocked URLs, extraction-empty outcomes, contradictory evidence, and failure modes grounded in real incident examples.
- Verify the exact consumer contract and connect benchmark evidence to the existing TSIC/World Intelligence acceptance path without duplicating their authority.
- Record per-version baselines and review dataset changes. Do not use a single blended score or describe the fixture baseline as factual accuracy.

W12 must remain operationally open until representative live observations, reviewed thresholds, and regression evidence are attached to an exact candidate revision.