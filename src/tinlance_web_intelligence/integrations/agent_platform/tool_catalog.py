"""TWI operation manifests for registration in the existing Platform MCP gateway.

TWI intentionally does not host a second MCP endpoint or duplicate Platform's MCP
identity, policy, approval, and audit gateway.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class PlatformToolContract:
    name: str
    operation: str
    description: str
    capability: str
    action: str
    resource_pattern: str
    required_scope: str
    input_schema: dict[str, Any]
    read_only: bool
    consequential: bool
    destructive: bool
    open_world: bool
    idempotency_argument: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


SEARCH_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["query", "idempotency_key"],
    "properties": {
        "query": {"type": "string", "minLength": 1, "maxLength": 400},
        "limit": {"type": "integer", "minimum": 1, "maximum": 20, "default": 10},
        "idempotency_key": {"type": "string", "minLength": 16, "maxLength": 256},
    },
}
FETCH_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["url", "idempotency_key"],
    "properties": {
        "url": {"type": "string", "format": "uri", "maxLength": 4096},
        "idempotency_key": {"type": "string", "minLength": 16, "maxLength": 256},
    },
}
JOB_ID_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["job_id"],
    "properties": {"job_id": {"type": "string", "minLength": 1, "maxLength": 64}},
}

TWI_PLATFORM_TOOLS: tuple[PlatformToolContract, ...] = (
    PlatformToolContract(
        name="twi_search",
        operation="twi.jobs.create_search",
        description="Submit a bounded web search and return a durable job reference.",
        capability="web.search",
        action="submit",
        resource_pattern="web://search/*",
        required_scope="twi:search",
        input_schema=SEARCH_SCHEMA,
        read_only=False,
        consequential=False,
        destructive=False,
        open_world=True,
        idempotency_argument="idempotency_key",
    ),
    PlatformToolContract(
        name="twi_fetch",
        operation="twi.jobs.create_fetch",
        description="Submit a policy-checked public web fetch and return a durable job reference.",
        capability="web.fetch",
        action="submit",
        resource_pattern="web://fetch/*",
        required_scope="twi:fetch",
        input_schema=FETCH_SCHEMA,
        read_only=False,
        consequential=False,
        destructive=False,
        open_world=True,
        idempotency_argument="idempotency_key",
    ),
    PlatformToolContract(
        name="twi_job_read",
        operation="twi.jobs.read",
        description="Read a job owned by the authenticated subject in the current tenant.",
        capability="web.job.read",
        action="read",
        resource_pattern="twi://jobs/{job_id}",
        required_scope="twi:jobs:read",
        input_schema=JOB_ID_SCHEMA,
        read_only=True,
        consequential=False,
        destructive=False,
        open_world=False,
    ),
    PlatformToolContract(
        name="twi_job_cancel",
        operation="twi.jobs.cancel",
        description="Request cancellation of a job owned by the authenticated subject.",
        capability="web.job.cancel",
        action="cancel",
        resource_pattern="twi://jobs/{job_id}",
        required_scope="twi:jobs:cancel",
        input_schema=JOB_ID_SCHEMA,
        read_only=False,
        consequential=True,
        destructive=False,
        open_world=False,
    ),
)
