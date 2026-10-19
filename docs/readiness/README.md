# W15 readiness evidence

`w15-gates.json` lists repository and external release gates. The builder records the full source Git SHA, stable evidence references, content SHA-256 values, and gate states; it never embeds the evidence content. It sorts gates and emits compact canonical JSON so the same source tree and revision produce identical bytes.

The `observed_at` field is the source revision's commit timestamp. It anchors the evidence index to its immutable revision; it is not a claim that an external owner attested the evidence at that time. Missing owners and evidence remain `not_evidenced`.

```bash
python scripts/build_w15_evidence_pack.py --gates docs/readiness/w15-gates.json --output dist/w15-evidence-pack.json
python scripts/validate_w15_evidence_pack.py --pack dist/w15-evidence-pack.json --revision "$(git rev-parse HEAD)"
```

The validator checks the exact required gate set against the reviewed registry, source revision, content hashes, expiry, metadata privacy, and fail-closed readiness. The repository evidence-export gate now references the API authorization/integrity tests; this does not mean the pinned Platform adapter has registered the export tool. The current consumer evidence includes a confirmed Platform monitor/evidence-export tool gap, a passing pinned World Intelligence schema compatibility check, and unevidenced TSIC conformance. A structurally valid pack reports `ready=false` while the Platform mismatch and branch governance, deployment security, privacy/risk ownership, SLO/on-call, live quality and release approval remain unresolved. Workflow configuration and synthetic fixtures cannot turn these gates to `pass`.
