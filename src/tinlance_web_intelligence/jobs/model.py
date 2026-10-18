"""Public job model and explicit state machine."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class Job:
    job_id: str
    tenant_id: str
    subject_id: str
    kind: str
    payload: dict[str, Any]
    status: JobStatus
    created_at: str
    updated_at: str
    attempts: int
    max_attempts: int
    result: dict[str, Any] | None = None
    error_code: str | None = None
    cancel_requested: bool = False
    idempotency_key: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class IdempotencyConflictError(ValueError):
    """A key was reused for a different request payload."""


class LeaseLostError(RuntimeError):
    """A worker attempted to mutate a job it no longer owns."""
