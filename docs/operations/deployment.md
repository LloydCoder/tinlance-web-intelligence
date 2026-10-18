# Deployment topology (W3 baseline)

W3 provides separate API and worker entry points. The API serves health probes and tenant-scoped job endpoints; the worker claims durable jobs and performs bounded acquisition. They share a SQLite database in this workstream, so the supported topology is a single node with a persistent volume. Do not run multiple replicas against a shared SQLite file.

## Required production configuration

- `TWI_ENV=production`.
- `TWI_DATABASE_PATH` points to a persistent writable volume; the volume must be backed up.
- `TWI_IDENTITY_ISSUER`, `TWI_IDENTITY_AUDIENCE`, and `TWI_IDENTITY_JWKS_URL` identify the Platform-issued token issuer and TWI resource audience.
- `TWI_BRAVE_SEARCH_API_KEY` is optional; store it in a secret manager, not a committed `.env` file.
- Restrict API ingress to the Platform gateway and trusted health probes. Apply network egress policy to API and worker containers.

W3 does not certify a production deployment. W6 must replace the single-node SQLite topology with the supported production persistence/replica strategy, add deployment manifests, run backup/recovery tests, and verify egress policy in the actual environment.
