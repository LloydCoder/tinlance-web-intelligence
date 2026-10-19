# W11 evidence provenance and data governance audit

**Status:** Repository implementation merged and exact-head CI-verified; operational exit gate remains open.

## Reviewed implementation

- Acquisition provenance manifests record requested/final URL fingerprints, HTTP status, content type, SHA-256 content digest, byte size, retrieval timestamp, redirect count, extractor version, and schema version.
- Provenance explicitly records acquisition/integrity facts and does not claim that source content is accurate, authoritative, safe, or true.
- Fetch-job completion validates the evidence pack: normalized artifact ID, valid content digest, parseable manifest, matching digest, matching status/content type, and matching timezone-aware retrieval timestamp.
- Freshness classification requires a caller-supplied maximum age and bounded clock-skew policy. Results are fresh, stale, or future_dated; freshness is not a truth or authority score.
- scripts/prune_job_data.py defaults to dry-run, requires a separate TWI_JOB_MAINTENANCE_DATABASE_URL, and requires --apply plus TWI_CONFIRM_JOB_DATA_PRUNE=YES for destructive redaction. Artifact retention remains a separate operation and credential.
- Backup/restore documentation now distinguishes artifact and job-data maintenance privileges.

## CI evidence

- Provenance and job-retention implementation merged in PR [#40](https://github.com/LloydCoder/tinlance-web-intelligence/pull/40), merge commit 18e38c370fc8409d1e863419e986187763232842. Exact-head CI passed in runs [#640](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39220354063) and [#639](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39220311644).
- Freshness and evidence-pack validation merged in PR [#44](https://github.com/LloydCoder/tinlance-web-intelligence/pull/44), merge commit b0a10ae3414af0d41f2dd16e1935aed2455efcab. Exact-head CI passed in run [#654](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39221617667): Python 3.12, Python 3.13, isolated browser/egress controls, container vulnerability policy, and reproducible release artifact validation all succeeded.

## Remaining exit gates

- Approve and configure a retention schedule and deletion policy for the target environment; verify the actual maintenance DSN's least-privilege grants.
- Review raw URL persistence. Job results include source_url, canonical_url, and extracted links, while artifact metadata can retain source URLs. Query parameters may contain secrets or personal data. Define and test a compatible redaction/minimization policy before private beta.
- Verify tenant-scoped artifact and job-result access against the deployed PostgreSQL roles and actual API/worker identities.
- Demonstrate retention dry-run, approved deletion/redaction, audit evidence, and recovery implications in the target deployment.
- Reconcile the evidence-pack schema against the exact World Intelligence consumer contract and TSIC conformance evidence.

Do not mark W11 release-ready or certify private beta until the remaining items have evidence tied to an exact release and target environment.