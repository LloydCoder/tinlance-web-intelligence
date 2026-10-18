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
VERIFY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["claims"],
    "properties": {
        "claims": {
            "type": "array",
            "minItems": 1,
            "maxItems": 20,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["claim_id", "statement", "citations"],
                "properties": {
                    "claim_id": {"type": "string", "pattern": "^[A-Za-z0-9._:-]{1,64}$"},
                    "statement": {"type": "string", "minLength": 1, "maxLength": 500},
                    "citations": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 4,
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["job_id", "quote"],
                            "properties": {
                                "job_id": {"type": "string", "minLength": 1, "maxLength": 64},
                                "quote": {"type": "string", "minLength": 8, "maxLength": 350},
                            },
                        },
                    },
                },
            },
        },
    },
}

JOB_ID_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["job_id"],
    "properties": {"job_id": {"type": "string", "minLength": 1, "maxLength": 64}},
}
BROWSER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["url", "idempotency_key"],
    "properties": {
        "url": {"type": "string", "format": "uri", "maxLength": 4096},
        "wait_until": {
            "type": "string",
            "enum": ["domcontentloaded", "load"],
            "default": "domcontentloaded",
        },
        "timeout_ms": {
            "type": "integer",
            "minimum": 1000,
            "maximum": 30000,
            "default": 15000,
        },
        "include_screenshot": {"type": "boolean", "default": False},
        "idempotency_key": {"type": "string", "minLength": 16, "maxLength": 256},
    },
}

EXPORT_SOURCE_EVIDENCE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "claim_id",
        "statement",
        "job_id",
        "quote",
        "idempotency_key",
        "run_id",
        "approval_id",
        "intent_fingerprint",
    ],
    "properties": {
        "claim_id": {"type": "string", "pattern": "^[A-Za-z0-9._:-]{1,64}$"},
        "statement": {"type": "string", "minLength": 1, "maxLength": 500},
        "job_id": {"type": "string", "minLength": 1, "maxLength": 64},
        "quote": {"type": "string", "minLength": 8, "maxLength": 350},
        "idempotency_key": {"type": "string", "pattern": "^[A-Za-z0-9._:-]{16,128}$"},
        "run_id": {"type": "string", "format": "uuid"},
        "approval_id": {"type": "string", "format": "uuid"},
        "intent_fingerprint": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
    },
}
EXPORT_STATUS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["event_id"],
    "properties": {"event_id": {"type": "string", "format": "uuid"}},
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
        name="twi_browser_navigate",
        operation="twi.jobs.create_browser",
        description="Capture a public web page in a fresh isolated read-only browser context.",
        capability="web.browser.navigate",
        action="navigate",
        resource_pattern="web://browser/*",
        required_scope="twi:browser",
        input_schema=BROWSER_SCHEMA,
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
        name="twi_research_verify",
        operation="twi.research.verify",
        description=(
            "Verify that each research citation references an authorized successful TWI "
            "fetch/browser job and that its quoted excerpt occurs in captured text; this "
            "does not determine factual truth."
        ),
        capability="web.research.verify",
        action="verify",
        resource_pattern="twi://research/verification/*",
        required_scope="twi:research:verify",
        input_schema=VERIFY_SCHEMA,
        read_only=True,
        consequential=False,
        destructive=False,
        open_world=False,
    ),
    PlatformToolContract(
        name="twi_world_intelligence_export",
        operation="twi.world_intelligence.export_source_evidence",
        description=(
            "Export a citation-verified claim as tenant-scoped candidate source evidence to "
            "World Intelligence. This is a state-changing operation and never creates canonical "
            "world state or asserts factual truth."
        ),
        capability="world-intelligence.source-evidence.export",
        action="submit",
        resource_pattern="world-intelligence://source-evidence/*",
        required_scope="twi:observations:export",
        input_schema=EXPORT_SOURCE_EVIDENCE_SCHEMA,
        read_only=False,
        consequential=True,
        destructive=False,
        open_world=False,
        idempotency_argument="idempotency_key",
    ),
    PlatformToolContract(
        name="twi_world_intelligence_export_status",
        operation="twi.world_intelligence.export_status",
        description=(
            "Read the status of a source-evidence export owned by the authenticated subject."
        ),
        capability="world-intelligence.source-evidence.read",
        action="read",
        resource_pattern="twi://world-intelligence/exports/{event_id}",
        required_scope="twi:observations:export:read",
        input_schema=EXPORT_STATUS_SCHEMA,
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
        consequential=False,
        destructive=False,
        open_world=False,
    ),
)
