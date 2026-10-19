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

Raw URLs, query values, tenant/subject IDs, credentials, request tokens, and billing payloads are excluded. Package integrity detects accidental or malicious modification; it is not a digital signature and does not prove that the upstream source was truthful.

## Availability and failure behavior

Exports require durable artifact content, a valid provenance manifest, and a full 40-character source revision supplied by deployment metadata. If any prerequisite is unavailable, export fails closed. Production deployments must use the shared PostgreSQL artifact store; process-local memory storage is for development/test only. The export is not a substitute for configured immutable retention, backup, or external audit archives.
