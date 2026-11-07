<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="apps/web/tinlyt-logo-dark-bg.svg">
    <img src="apps/web/tinlyt-logo-light-bg.svg" width="220" alt="Tinlyt">
  </picture>
</p>

<h1 align="center">Tinlyt</h1>
<p align="center"><strong>Discover sources. Verify claims. Preserve evidence.</strong></p>
<p align="center">Evidence-first web intelligence for research teams, developers, and governed AI agents — turning web acquisition into traceable, reviewable evidence.</p>
<p align="center">
  <a href="https://github.com/LloydCoder/tinlance-web-intelligence/actions/workflows/ci.yml"><img alt="Python CI" src="https://github.com/LloydCoder/tinlance-web-intelligence/actions/workflows/ci.yml/badge.svg?branch=main"></a>
  <a href="https://github.com/LloydCoder/tinlance-web-intelligence/actions/workflows/frontend.yml"><img alt="Frontend CI" src="https://github.com/LloydCoder/tinlance-web-intelligence/actions/workflows/frontend.yml/badge.svg?branch=main"></a>
  <a href="https://scorecard.dev/viewer/?uri=github.com/LloydCoder/tinlance-web-intelligence"><img alt="OpenSSF Scorecard" src="https://api.scorecard.dev/projects/github.com/LloydCoder/tinlance-web-intelligence/badge"></a>
  <a href="https://github.com/LloydCoder/tinlance-web-intelligence/blob/main/LICENSE"><img alt="License: Apache-2.0" src="https://img.shields.io/github/license/LloydCoder/tinlance-web-intelligence"></a>
</p>
<p align="center">
  <a href="https://tinlyt-web.vercel.app">Product site</a> · <a href="docs/README.md">Documentation</a> · <a href="docs/api/">API reference</a> · <a href="CONTRIBUTING.md">Contributing</a> · <a href="SECURITY.md">Security</a>
</p>

## Product preview

Explore the [public Tinlyt product site](https://tinlyt-web.vercel.app). Its workflow panel is explicitly illustrative; it is not a live acquisition or verification result. The authenticated workspace remains dependent on approved identity and API deployment configuration.

> **Project status:** Tinlyt is under active development. Repository implementation and CI evidence do not certify a live deployment, private beta, or general availability. See [release readiness](docs/operations/private-beta-readiness.md).

## What Tinlyt does

Tinlyt is evidence-first web intelligence infrastructure for research teams, developers, and governed AI agents. It provides controlled web search, retrieval, extraction, isolated browser acquisition, source provenance, claim-to-citation checks, and exportable evidence packages.

The system makes acquisition inspectable: what was requested, what was retrieved, how it was captured, and which evidence supports a finding. Retrieval and citation matching do **not** independently establish factual truth or source authority.

## Why this architecture

| Need | Tinlyt approach |
| --- | --- |
| Traceable research | Preserve acquisition metadata and source-linked observations. |
| Safer web access | Validate destinations and redirects, bound resource use, and isolate browser execution behind controlled egress. |
| Governed agent use | Integrate with Tinlance Agent Platform contracts rather than creating a parallel identity or execution authority. |
| Reviewable evidence | Export versioned packages with captured bytes, provenance, and integrity checks. |
| Ongoing observation | Store tenant-scoped monitor definitions and explicit capture runs; recurrence belongs to Agent OS. |

Tinlyt is not a general-purpose chatbot, a truth oracle, or an independent agent authority plane.

## Quick start

This starts the local API in development mode and checks liveness. It does not configure a live identity provider or external search credentials.

```bash
git clone https://github.com/LloydCoder/tinlance-web-intelligence.git
cd tinlance-web-intelligence
make install
python -m uvicorn apps.api.main:app --reload
```

In a second terminal:

```bash
curl --fail http://127.0.0.1:8000/health/live
```

Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) for the development OpenAPI interface. The local development verifier denies protected API requests by default; configure the approved Platform identity integration before submitting authenticated jobs.

## Installation

### Prerequisites

| Component | Requirement |
| --- | --- |
| Python | 3.12 or 3.13 |
| Node.js | 22.x, for frontend work |
| PostgreSQL | Required for staging/production; local development can use SQLite |
| Docker Compose | Required for containerized staging/browser-isolation topologies |

### Python API and workers

For a development checkout:

```bash
make install
make check
```

For a runtime-only Python installation:

```bash
python -m pip install .
```

Package metadata and pinned development dependencies are in [pyproject.toml](pyproject.toml) and [requirements-dev.txt](requirements-dev.txt). The canonical repository validation command is `make check`.

### Frontend

```bash
cd apps/web
npm ci --ignore-scripts --no-audit --no-fund
npm run check
npm audit --audit-level=high
```

The frontend build writes generated output to `apps/web/dist/`. Frontend checks do not replace API or Platform identity configuration.

### Containerized deployment

Deployment definitions are maintained under [deployments/compose/](deployments/compose/). The staging topology requires externally managed PostgreSQL, Platform identity/JWKS settings, and runtime secrets. Do not treat the local browser-isolation Compose file as a production deployment profile. Review [operations documentation](docs/operations/) before exposing services.

## Usage

### Check service health

With the API running locally:

```bash
curl --fail http://127.0.0.1:8000/health/live
curl --fail http://127.0.0.1:8000/health/ready
```

### Submit an authenticated search job

Use this example only in an environment where the approved Tinlance Agent Platform identity provider is configured and the caller has the `twi:search` scope. A local development instance with the default deny-all verifier will reject this request.

```bash
export TWI_API_URL="https://your-configured-twi-api.example"
export TWI_ACCESS_TOKEN="replace-with-a-short-lived-platform-access-token"
IDEMPOTENCY_KEY="$(python -c 'import uuid; print(uuid.uuid4())')"

curl --fail-with-body --request POST "$TWI_API_URL/v1/jobs" \
  --header "Authorization: Bearer $TWI_ACCESS_TOKEN" \
  --header "Content-Type: application/json" \
  --header "Idempotency-Key: $IDEMPOTENCY_KEY" \
  --data '{"kind":"search","payload":{"query":"primary sources for a research question","limit":5}}'
```

Job creation returns `202 Accepted`. The idempotency key must be 16–256 printable ASCII characters. Reuse the same key only when retrying the same logical request. See [Jobs API v1](docs/api/jobs-v1.md) for scopes, payload constraints, job states, cancellation, and error behavior.

### Export evidence

A successful fetch job can expose `GET /v1/jobs/{job_id}/evidence` to a caller with `twi:evidence:export`. The export contains captured source bytes and acquisition provenance. It is integrity-checked, but it is not digitally signed and does not prove that the source is accurate. See [Evidence Export API v1](docs/api/evidence-packages-v1.md).

## Configuration

Start with [.env.example](.env.example). Never commit populated secrets. This table lists important settings; it is not an exhaustive substitute for the validated configuration model.

| Variable | Development default | Purpose |
| --- | --- | --- |
| `TWI_ENV` | `development` | Runtime environment: development, test, staging, or production |
| `TWI_DATABASE_PATH` | `./var/twi.sqlite3` | Local SQLite path |
| `TWI_DATABASE_URL` | unset | PostgreSQL DSN; staging/production require `sslmode=verify-full` |
| `TWI_IDENTITY_ISSUER` | unset | Platform token issuer |
| `TWI_IDENTITY_AUDIENCE` | unset | TWI API audience |
| `TWI_IDENTITY_JWKS_URL` | unset | HTTPS JWKS endpoint |
| `TWI_BROWSER_ENABLED` | `false` | Enables browser acquisition when isolated services are configured |
| `TWI_BRAVE_SEARCH_API_KEY` | unset | Optional Brave Search provider credential |
| `TWI_SOURCE_REVISION` | unset | Full 40-character commit SHA used by evidence exports |
| `TWI_OTEL_EXPORTER_OTLP_ENDPOINT` | unset | Optional OTLP/HTTP trace collector endpoint |

Production additionally requires the approved Platform token verifier, an entitlement resolver from the approved billing boundary, durable PostgreSQL persistence, and required worker/deployment controls. See [configuration validation](src/tinlance_web_intelligence/config.py) and [staging Compose](deployments/compose/staging.yml).

## Capabilities

| Area | Repository capability | Boundary or qualification |
| --- | --- | --- |
| Search | Provider-backed search adapter | Provider credentials and quotas are deployment-specific. |
| Fetch and extraction | Controlled HTTP acquisition and content extraction | URL, DNS/IP, redirect, timeout, and response-size controls apply. |
| Browser acquisition | Isolated browser worker, broker, and egress proxy topology | Disabled by default; deployment isolation must be verified. |
| Jobs API | Authenticated, tenant-scoped job lifecycle | Requires Platform-issued identity and operation scopes. |
| Claim checks | Compare claims and citations against captured text | Quote matching is not a factual-truth verdict. |
| Evidence export | Versioned package with captured bytes and provenance | Integrity checking is not a digital signature or source-truth guarantee. |
| Monitors | Tenant-scoped definitions and explicit capture runs | Agent OS owns recurrence and scheduling. |
| Usage | Tenant-scoped usage facts and quota interfaces | Not a statement of invoice, payment settlement, or provider billing status. |
| Frontend | Tinlyt website and workspace foundation | Live authenticated journeys depend on approved identity and API deployment configuration. |

## Documentation

The [documentation index](docs/README.md) organizes existing project material.

| Topic | Start here |
| --- | --- |
| Architecture and authority boundaries | [Component boundaries](docs/architecture/component-boundaries.md) |
| Workstream status | [Phase ledger](docs/roadmap/phases.md) |
| Jobs and acquisition | [Jobs API v1](docs/api/jobs-v1.md) |
| Evidence packages | [Evidence Export API v1](docs/api/evidence-packages-v1.md) |
| Monitors | [Monitor API v1](docs/api/monitors-v1.md) |
| Usage and quotas | [Usage API v1](docs/api/usage-v1.md) |
| SSRF and egress | [SSRF controls](docs/security/ssrf-controls.md) |
| Threat model | [Threat model](docs/security/threat-model.md) |
| Operations and recovery | [Operations documentation](docs/operations/) |
| Product and frontend contracts | [Frontend contract](docs/product/tinlyt-frontend-contract.md) |
| Evaluation methodology | [TWI benchmark](docs/evaluation/twi-benchmark.md) |
| Release gates | [Private-beta readiness](docs/operations/private-beta-readiness.md) |

## Contributing

Contributions are welcome through focused pull requests. Read [CONTRIBUTING.md](CONTRIBUTING.md), follow security and authority boundaries, add tests for behavior changes, and run `make check` before requesting review.

## License and acknowledgements

Tinlyt is distributed under the [Apache License 2.0](LICENSE). Third-party dependencies retain their respective licenses; see package metadata and dependency notices. The Tinlyt wordmark uses outlined artwork in the repository's web assets. The Tinlyt name and logo are project identity assets and are not represented here as trademark-cleared.

<details>
<summary>Roadmap and release status</summary>

Workstream acceptance and outstanding external gates are tracked in the [phase ledger](docs/roadmap/phases.md). The current release decision remains **NOT CERTIFIED** until deployment, branch governance, privacy, SLO/on-call, security, interoperability, and owner-approval evidence is complete.

</details>

<details>
<summary>Troubleshooting</summary>

- **Protected API routes return 401 locally:** expected with the default deny-all development verifier. Configure the approved Platform identity integration; do not disable authorization to make the example work.
- **Staging startup rejects the database URL:** staging/production require PostgreSQL with `sslmode=verify-full`.
- **Browser jobs are unavailable:** browser acquisition is disabled by default and requires the isolated broker, worker, proxy, and deployment configuration.
- **Evidence export is unavailable:** check successful fetch-job state, caller scope, durable artifact storage, provenance, and a full source revision.

</details>

<details>
<summary>Support</summary>

Use GitHub Issues for reproducible defects and feature proposals. For private security reports, follow [SECURITY.md](SECURITY.md). General project guidance is in [SUPPORT.md](SUPPORT.md).

</details>
