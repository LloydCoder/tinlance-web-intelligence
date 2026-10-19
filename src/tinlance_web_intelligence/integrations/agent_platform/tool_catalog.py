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
EVIDENCE_EXPORT_SCHEMA: dict[str, Any] = {
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
MONITOR_ID_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["monitor_id"],
    "properties": {"monitor_id": {"type": "string", "minLength": 1, "maxLength": 64}},
}
MONITOR_CREATE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["target_url", "idempotency_key"],
    "properties": {
        "target_url": {"type": "string", "format": "uri", "maxLength": 4096},
        "policy": {
            "type": "object",
            "additionalProperties": False,
            "properties": {"max_bytes": {"type": "integer", "minimum": 1}},
        },
        "idempotency_key": {"type": "string", "minLength": 16, "maxLength": 256},
    },
}
MONITOR_RUN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["monitor_id", "idempotency_key"],
    "properties": {
        "monitor_id": {"type": "string", "minLength": 1, "maxLength": 64},
        "idempotency_key": {"type": "string", "minLength": 16, "maxLength": 256},
    },
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
        name="twi_evidence_export",
        operation="twi.jobs.export_evidence",
        description=(
            "Export integrity-checked acquisition bytes and provenance for a successful fetch job; "
            "does not assert source truth or authority."
        ),
        capability="web.evidence.export",
        action="read",
        resource_pattern="twi://jobs/{job_id}/evidence",
        required_scope="twi:evidence:export",
        input_schema=EVIDENCE_EXPORT_SCHEMA,
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
    PlatformToolContract(
        name="twi_monitor_create",
        operation="twi.monitors.create",
        description="Create a tenant-scoped monitor for a policy-checked public web URL.",
        capability="web.monitor.create",
        action="create",
        resource_pattern="web://monitors/*",
        required_scope="twi:monitors:write",
        input_schema=MONITOR_CREATE_SCHEMA,
        read_only=False,
        consequential=False,
        destructive=False,
        open_world=False,
        idempotency_argument="idempotency_key",
    ),
    PlatformToolContract(
        name="twi_monitor_read",
        operation="twi.monitors.read",
        description="Read monitor state within the authenticated tenant and subject scope.",
        capability="web.monitor.read",
        action="read",
        resource_pattern="twi://monitors/{monitor_id}",
        required_scope="twi:monitors:read",
        input_schema=MONITOR_ID_SCHEMA,
        read_only=True,
        consequential=False,
        destructive=False,
        open_world=False,
    ),
    PlatformToolContract(
        name="twi_monitor_run",
        operation="twi.monitors.run",
        description="Enqueue one idempotent monitor capture; recurrence remains with Agent OS.",
        capability="web.monitor.run",
        action="submit",
        resource_pattern="twi://monitors/{monitor_id}/runs",
        required_scope="twi:monitors:write",
        input_schema=MONITOR_RUN_SCHEMA,
        read_only=False,
        consequential=False,
        destructive=False,
        open_world=True,
        idempotency_argument="idempotency_key",
    ),
    PlatformToolContract(
        name="twi_monitor_pause",
        operation="twi.monitors.pause",
        description="Pause future monitor run enqueues while existing work drains.",
        capability="web.monitor.pause",
        action="pause",
        resource_pattern="twi://monitors/{monitor_id}",
        required_scope="twi:monitors:write",
        input_schema=MONITOR_ID_SCHEMA,
        read_only=False,
        consequential=False,
        destructive=False,
        open_world=False,
    ),
    PlatformToolContract(
        name="twi_monitor_resume",
        operation="twi.monitors.resume",
        description="Resume a paused monitor so Agent OS may enqueue future runs.",
        capability="web.monitor.resume",
        action="resume",
        resource_pattern="twi://monitors/{monitor_id}",
        required_scope="twi:monitors:write",
        input_schema=MONITOR_ID_SCHEMA,
        read_only=False,
        consequential=False,
        destructive=False,
        open_world=False,
    ),
    PlatformToolContract(
        name="twi_monitor_delete",
        operation="twi.monitors.delete",
        description="Redact and tombstone a monitor and its stored change summaries.",
        capability="web.monitor.delete",
        action="delete",
        resource_pattern="twi://monitors/{monitor_id}",
        required_scope="twi:monitors:delete",
        input_schema=MONITOR_ID_SCHEMA,
        read_only=False,
        consequential=False,
        destructive=True,
        open_world=False,
    ),
)
