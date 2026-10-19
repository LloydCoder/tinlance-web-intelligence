# TWI reproducible evaluation benchmark

## Purpose and boundaries

The benchmark evaluates recorded TWI observations without network access. It is intentionally separate from FAS-Bench and does not create a new identity, policy, approval, evidence, or World Intelligence authority. It measures observable pipeline properties; it does not prove that retrieved sources are authoritative or that claims are true.

## Run

From the repository root, use a fixed evaluation timestamp:

```bash
python scripts/evaluate_twi.py \
  --dataset benchmarks/twi/v1/cases.json \
  --results benchmarks/twi/v1/sample_results.json \
  --now 2026-10-19T12:00:00Z \
  --json-out /tmp/twi-evaluation.json \
  --markdown-out /tmp/twi-evaluation.md
```

The explicit `--now` prevents wall-clock drift. The report includes SHA-256 hashes of the exact dataset and results bytes. Re-running the same inputs and timestamp produces the same report. The CLI does not perform web requests or emit raw source URLs in the report.

## Metrics

- **Retrieval recall:** expected normalized URLs present in retrieved observations divided by expected URLs.
- **Source-diversity coverage:** expected hostnames represented in retrieved observations divided by expected hostnames.
- **Extraction coverage:** expected phrases present in extracted title/text divided by expected phrases.
- **Citation-grounding rate:** claims whose cited URLs are present and whose non-stopword tokens have at least 50% lexical overlap with one cited source. This is a heuristic, not semantic entailment.
- **Freshness rate:** retrieved items within the case's explicit maximum age and five-minute future-clock-skew allowance. Cases with no retrieved evidence have no freshness score.
- **Failure-calibration accuracy:** exact match between expected and observed failure mode. This is classification agreement, not probabilistic calibration.

Metrics are macro-averaged by case, with undefined metrics excluded. There is deliberately no single blended quality score that could hide a serious weakness.

## Dataset and result contract

The versioned dataset under `benchmarks/twi/v1/` contains gold URL/domain/phrase expectations, a positive max-age, and the expected failure mode. The result file supplies the observed retrieved records, timestamped evidence, claims and citation URLs, plus the observed failure mode. The evaluator rejects duplicate case IDs, missing/extra result cases, malformed timestamps, URLs with userinfo, and mismatched dataset IDs.

The checked-in sample observations include a grounded success, stale evidence, and a missing-source/unsupported-claim case. They are contract fixtures, not an accuracy claim about live web sources. Add new benchmark cases only with reviewable rationale and expected outcomes; bump the dataset version when semantics change.
