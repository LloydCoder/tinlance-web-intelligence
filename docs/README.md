# Tinlyt documentation

This index helps readers find the right material without duplicating detailed engineering records. Implementation contracts and readiness evidence stay close to the code they govern.

## Start here

| Reader goal | Recommended path |
| --- | --- |
| Understand system boundaries | [Component boundaries](architecture/component-boundaries.md) |
| Run the project locally | [Root README — Quick start](../README.md#quick-start) |
| Integrate with the API | [Jobs API v1](api/jobs-v1.md) |
| Understand captured evidence | [Evidence Export API v1](api/evidence-packages-v1.md) |
| Operate monitors | [Monitor API v1](api/monitors-v1.md) |
| Read usage facts | [Usage API v1](api/usage-v1.md) |
| Assess security controls | [Threat model](security/threat-model.md) and [SSRF controls](security/ssrf-controls.md) |
| Prepare a deployment | [Operations documentation](operations/) and [staging Compose](../deployments/compose/staging.yml) |
| Understand product/frontend boundaries | [Tinlyt frontend contract](product/tinlyt-frontend-contract.md) |
| Track implementation and external gates | [Workstream phase ledger](roadmap/phases.md) and [private-beta readiness](operations/private-beta-readiness.md) |
| Understand evaluation limits | [TWI benchmark methodology](evaluation/twi-benchmark.md) |

## Documentation map

This is a practical Diátaxis-style navigation map. Existing records remain in their established directories; not every record is a tutorial.

| Documentation mode | Location | Contents |
| --- | --- | --- |
| Tutorials | [Root Quick start](../README.md#quick-start) | First local API startup and health check |
| How-to guides | [Operations](operations/) · [Security](security/) | Deployment, backup/restore, recovery, SSRF and isolation procedures |
| Explanation | [Architecture](architecture/) · [Product](product/) · [Evaluation](evaluation/) | Authority boundaries, design decisions, product contracts, evaluation methodology |
| Reference | [API](api/) · [Schemas](../schemas/) · [Contracts](../contracts/) | Endpoints, payloads, schemas, and consumer interfaces |
| Release evidence | [Readiness](readiness/) · [Audits](audits/) · [Evidence](evidence/) | Exact-commit CI evidence, audits, gate state, and release decisions |
| Planning | [Roadmap](roadmap/) · [Commercial](commercial/) | Workstream sequencing and commercial policy |

## Documentation rules

- Treat code, schemas, migrations, and executable tests as authoritative for implemented behavior.
- Bind claims about CI to an exact commit and workflow run.
- Keep repository implementation status separate from deployment readiness and release certification.
- Update relevant API contracts, tests, operational runbooks, and this index when a change affects them.
- Prefer relative links so documentation remains useful in forks and local clones.
- Do not describe retrieval, quote matching, or digest validation as proof of factual truth.
