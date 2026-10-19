"""Immutable monitor definitions and bounded capture outcomes."""

from __future__ import annotations

import datetime
import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class MonitorStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    DELETED = "deleted"


class MonitorRunStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class IdempotencyConflictError(ValueError):
    """An idempotency key was reused for a different monitor request."""


class BaselineConflictError(RuntimeError):
    """A monitor baseline changed since a worker started its capture."""


class MonitorDeletedError(RuntimeError):
    """A queued monitor run cannot execute because its monitor was deleted."""


_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def normalize_monitor_policy(policy: dict[str, Any]) -> dict[str, int]:
    """Accept only the optional positive response-byte cap used by safe acquisition."""
    if set(policy) - {"max_bytes"}:
        raise ValueError("unsupported monitor policy field")
    if "max_bytes" not in policy:
        return {}
    max_bytes = policy["max_bytes"]
    if not isinstance(max_bytes, int) or isinstance(max_bytes, bool) or max_bytes < 1:
        raise ValueError("monitor max_bytes must be a positive integer")
    return {"max_bytes": max_bytes}


@dataclass(frozen=True, slots=True)
class Monitor:
    monitor_id: str
    tenant_id: str
    subject_id: str
    target_url: str
    policy: dict[str, Any]
    status: MonitorStatus
    baseline_digest: str | None
    baseline_observed_at: datetime.datetime | None
    baseline_version: int
    created_at: datetime.datetime
    updated_at: datetime.datetime
    idempotency_key: str


@dataclass(frozen=True, slots=True)
class MonitorRunResult:
    monitor_id: str
    job_id: str
    status: MonitorRunStatus
    previous_digest: str | None
    current_digest: str | None
    changed: bool | None
    observed_at: datetime.datetime
    changed_units: int

    def __post_init__(self) -> None:
        for digest in (self.previous_digest, self.current_digest):
            if digest is not None and not _SHA256.fullmatch(digest):
                raise ValueError("monitor result digests must be lowercase SHA-256 values")
        if not 0 <= self.changed_units <= 10000:
            raise ValueError("changed_units must be between 0 and 10000")
        if self.status is MonitorRunStatus.SUCCEEDED and self.current_digest is None:
            raise ValueError("successful monitor results require a current digest")

