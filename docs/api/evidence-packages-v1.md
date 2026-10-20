# Evidence Export API v1

## Endpoint

`GET /v1/jobs/{job_id}/evidence`

Requires a verified Agent Platform principal with `twi:evidence:export`. The job must be a successful `fetch` job belonging to the verified principal's tenant and subject. Caller-supplied tenant or subject identifiers are not accepted. Missing or out-of-scope jobs return the same `404` response to avoid cross-tenant disclosure.

The response is a deterministic JSON evidence package with media type `application/vnd.tinlance.twi-evidence+json`. Clients should store the exact response bytes and verify them using the package validator or another implementation of schema `schemas/twi-evidence-package-v1.schema.json`.

## Package contents

- Full source commit SHA, stable export identifier, artifact ID, byte size, content type, and SHA-256 digest.
- Base64-encoded captured bytes (maximum 20 MB before encoding).
- Versioned acquisition provenance: requested/final URL fingerprints, status, retrieval time, redirect count, and extractor version.
- Explicit interpretation metadata: provenance is an acquisition observation; source truth and source authority are not assessed.

Raw source URLs and their query parameters are excluded from package metadata, as are tenant/subject IDs and billing payloads. Captured bytes are included unchanged and may themselves contain personal data, credentials, tokens, or query-like text from the source page; treat the export as customer data and apply the approved access and retention policy. Package integrity detects modification; it is not a digital signature and does not prove that the upstream source was truthful.

## Availability and failure behavior

Exports require durable artifact content, a valid provenance manifest, and a full 40-character source revision supplied by deployment metadata. If any prerequisite is unavailable, export fails closed. Production deployments must use the shared PostgreSQL artifact store; process-local memory storage is for development/test only. The export is not a substitute for configured immutable retention, backup, or external audit archives.

## Frontend client requirements

- Require the exact vendor media type (parameters such as `charset=utf-8` may follow the media type) and reject other JSON media types for this endpoint.
- Read the response with a strict byte bound (30,000,000 bytes, including package metadata/base64 expansion) before parsing. Reject a declared or streamed body that exceeds the bound.
- Preserve the original response bytes in memory while separately parsing and validating the package. Validate the schema version, metadata consistency, decoded byte size, and SHA-256 of the captured bytes before enabling download.
- The download action must write the original response bytes; do not reconstruct the package with `JSON.stringify`, which can change whitespace or byte representation.
- Display provenance fields and URL fingerprints using text-only DOM APIs. Do not insert captured HTML into the application DOM or infer raw URLs from their hashes.
- Clear the in-memory package and byte buffer on sign-out or job/session change. Do not persist evidence in browser storage or analytics.
- State clearly that a matching digest validates the captured content against package metadata; it is not a digital signature, a tamper-proof guarantee, a source-authority assessment, or a factual-truth verdict.
