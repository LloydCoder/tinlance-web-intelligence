# W15-B — Customer-Facing Provenance and Evidence Export

**Status:** implementation in progress. This contract defines evidence export; it does not certify external retention or customer privacy configuration.

## Objective

Expose a tenant-authorized, reproducible evidence package for successful fetch jobs by reusing the existing artifact store and acquisition provenance manifest. The package must preserve the relationship between source observation, captured bytes, acquisition metadata, extractor version, and source revision.

## Existing capabilities to reuse

- `contracts.provenance.AcquisitionProvenance` already captures requested/final URL fingerprints, HTTP status, media type, content digest, byte size, retrieval time, redirect count, and extractor version.
- `artifacts.ArtifactStore` and `PostgresArtifactStore` already provide tenant-scoped content-addressed storage and SHA-256 verification.
- Fetch jobs already return `artifact_id`, `content_sha256`, and a provenance manifest.
- The existing W15 readiness evidence pack is a separate release-readiness artifact; this customer evidence package must not replace it.

## Contract

- Export only successful fetch jobs readable by the verified Agent Platform principal.
- Derive tenant and subject exclusively from the verified principal. Do not accept tenant IDs or subject IDs from query/body parameters.
- Require a dedicated `twi:evidence:export` scope, in addition to the job's tenant/subject ownership check.
- Resolve bytes by the recorded SHA-256 and verified tenant scope. Fail closed on absent content, digest mismatch, malformed provenance, or unavailable source revision.
- Package format is `application/vnd.tinlance.twi-evidence+json`, schema `1.0.0`; maximum source content is 20 MB and maximum encoded package is 30 MB.
- Export includes the exact captured bytes as base64, digest and size, content type, acquisition provenance, extractor version, and a full 40-character source commit SHA.
- Export metadata excludes raw source URLs, URL query parameters, tenant/subject identifiers, and billing data. Captured bytes remain unchanged and can themselves contain sensitive source text; the API is not a content-redaction layer.
- Package bytes and `export_id` are deterministic for the same artifact, provenance, and source revision.
- Verification detects content tampering, manifest mismatch, source revision mismatch when requested, and noncanonical serialization.
- Explicitly state that provenance is an acquisition observation, not a claim of source truth, safety, completeness, or authority.
- Keep the export format versioned and additive-compatible; breaking changes require a new schema version and fixture.

## Acceptance evidence

1. Unit tests validate byte stability, manifest linkage, content hash, source revision, package ID, and canonical JSON.
2. API tests cover authentication, dedicated scope, cross-tenant non-disclosure, wrong job type/state, missing artifact, malformed manifest, missing source revision, and content tampering.
3. Schema validation runs in CI against positive and adversarial fixtures.
4. PostgreSQL integration tests verify tenant-scoped artifact retrieval and content integrity when `TWI_TEST_POSTGRES_DSN` is available. Skips must remain explicitly reported.
5. API docs, schemas, README, and readiness records describe the implemented boundary without claiming external immutable retention or customer-configured privacy guarantees.

## Authority boundary

TWI exports acquisition facts and bytes only. Agent Platform retains identity, authorization, approval, and audit authority. World Intelligence retains canonical world state and truth judgments. TWI does not make source-truth judgments or mutate canonical world state.
