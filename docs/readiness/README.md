# W15 readiness evidence

`w15-gates.json` lists repository and external release gates. The builder records the full source Git SHA, stable evidence references, content SHA-256 values, and gate states; it never embeds the evidence content. It sorts gates and emits compact canonical JSON so the same source tree and revision produce identical bytes.

The `observed_at` field is the source revision's commit timestamp. It anchors the evidence index to its immutable revision; it is not a claim that an external owner attested the evidence at that time. Missing owners and evidence remain `not_evidenced`.

```bash
python scripts/build_w15_evidence_pack.py --gates docs/readiness/w15-gates.json --output dist/w15-evidence-pack.json
python scripts/validate_w15_evidence_pack.py --pack dist/w15-evidence-pack.json --revision "$(git rev-parse HEAD)"
```

The validator checks the exact required gate set against the reviewed registry, source revision, content hashes, expiry, metadata privacy, and fail-closed readiness. The repository evidence-export gate references the API authorization/integrity tests. The current Platform consumer snapshot is pinned to `tinlance-agent-platform` revision `c5a080c1fb4df68e45070f8cddfc30bf81edd7bb` and records all 15 registered TWI tools, including all six monitor operations and `twi_evidence_export`; source-evidence export and destructive monitor deletion are approval-gated. The historical failed snapshot remains preserved for audit traceability. The pinned World Intelligence schema compatibility check passes. TSIC conformance remains `not_evidenced`: a required TSIC contract and green generic TSIC workflows do not by themselves prove that every TWI requirement was exercised against a deployed consumer. The W15 `external.ci_run` gate is now bound to the exact-main CI run and a hashable evidence record. A structurally valid pack still reports `ready=false` because effective branch governance, deployed API/Platform identity, deployment security, witnessed recovery from a real encrypted backup, privacy/risk ownership, SLO/on-call, live quality, and authorized release approval remain unresolved. Workflow configuration and synthetic fixtures cannot turn these external gates to `pass`.

## GA v1 release decision

The versioned GA contract lives in `docs/releases/ga-v1-contract.json`, with the decision schema in `schemas/ga-v1-release-decision.schema.json`. Run `python scripts/validate_ga_v1_contract.py` or `make ga-contract-check` to verify the gate registry and fail-closed decision rules. An unbound draft uses a null source revision and cannot be approved. A release candidate must bind the exact source SHA, evidence-pack bytes and digest, benchmark threshold approval, security review, residual-risk disposition, customer constraints and named release approval. The validator cannot authenticate external owners or replace deployment evidence. Current status remains `not_certified` because the readiness registry contains failed and unevidenced external gates.
