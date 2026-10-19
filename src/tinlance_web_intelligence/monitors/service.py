"""Acquisition orchestration and deterministic content-change comparison."""

from __future__ import annotations

import datetime
import hashlib
import unicodedata
from typing import Any, Protocol

from tinlance_web_intelligence.acquisition.models import AcquiredPage
from tinlance_web_intelligence.jobs.model import Job
from tinlance_web_intelligence.monitors.model import (
    BaselineConflictError,
    Monitor,
    MonitorRunResult,
    MonitorRunStatus,
    MonitorStatus,
)
from tinlance_web_intelligence.persistence.monitor_protocol import MonitorRepository
from tinlance_web_intelligence.persistence.protocols import JobRepository

_MAX_NORMALIZED_TEXT_CHARS = 500_000


class PageAcquirer(Protocol):
    async def acquire_page(
        self, url: str, *, tenant_id: str, max_bytes: int | None = None
    ) -> AcquiredPage: ...


def normalize_text_digest(text: str) -> str:
    """Hash bounded Unicode-normalized text with deterministic whitespace folding."""
    if len(text) > _MAX_NORMALIZED_TEXT_CHARS:
        raise ValueError("monitor extracted text exceeds the configured comparison limit")
    normalized = " ".join(unicodedata.normalize("NFKC", text).split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class MonitorService:
    """Monitor lifecycle service; recurrence stays with the Agent OS."""

    def __init__(
        self,
        *,
        repository: MonitorRepository,
        job_repository: JobRepository | None = None,
        acquisition: PageAcquirer | None = None,
    ) -> None:
        self.repository = repository
        self.job_repository = job_repository
        self.acquisition = acquisition

    def create_monitor(
        self,
        *,
        tenant_id: str,
        subject_id: str,
        target_url: str,
        policy: dict[str, object],
        idempotency_key: str,
    ) -> Monitor:
        return self.repository.create(
            tenant_id=tenant_id,
            subject_id=subject_id,
            target_url=target_url,
            policy=policy,
            idempotency_key=idempotency_key,
        )

    def enqueue_run(
        self,
        *,
        tenant_id: str,
        subject_id: str,
        monitor_id: str,
        idempotency_key: str,
        traceparent: str | None = None,
    ) -> Job:
        if self.job_repository is None:
            raise RuntimeError("monitor run queue is not configured")
        monitor = self.repository.get(
            tenant_id=tenant_id,
            subject_id=subject_id,
            monitor_id=monitor_id,
        )
        if monitor is None:
            raise KeyError("monitor not found")
        if monitor.status is not MonitorStatus.ACTIVE:
            raise ValueError("monitor is not active")
        return self.job_repository.create(
            tenant_id=tenant_id,
            subject_id=subject_id,
            kind="monitor",
            payload={
                "monitor_id": monitor.monitor_id,
                "baseline_version": monitor.baseline_version,
            },
            idempotency_key=idempotency_key,
            traceparent=traceparent,
        )

    def pause(self, *, tenant_id: str, subject_id: str, monitor_id: str) -> Monitor:
        current = self.repository.get(
            tenant_id=tenant_id, subject_id=subject_id, monitor_id=monitor_id
        )
        if current is None:
            raise KeyError("monitor not found")
        if current.status is MonitorStatus.DELETED:
            raise ValueError("deleted monitors cannot be paused")
        if current.status is MonitorStatus.PAUSED:
            return current
        monitor = self.repository.set_status(
            tenant_id=tenant_id,
            subject_id=subject_id,
            monitor_id=monitor_id,
            status=MonitorStatus.PAUSED.value,
        )
        if monitor is None:
            raise KeyError("monitor not found")
        return monitor

    def resume(self, *, tenant_id: str, subject_id: str, monitor_id: str) -> Monitor:
        current = self.repository.get(
            tenant_id=tenant_id, subject_id=subject_id, monitor_id=monitor_id
        )
        if current is None:
            raise KeyError("monitor not found")
        if current.status is MonitorStatus.DELETED:
            raise ValueError("deleted monitors cannot be resumed")
        if current.status is MonitorStatus.ACTIVE:
            return current
        monitor = self.repository.set_status(
            tenant_id=tenant_id,
            subject_id=subject_id,
            monitor_id=monitor_id,
            status=MonitorStatus.ACTIVE.value,
        )
        if monitor is None:
            raise KeyError("monitor not found")
        return monitor

    def delete(self, *, tenant_id: str, subject_id: str, monitor_id: str) -> Monitor:
        monitor = self.repository.redact(
            tenant_id=tenant_id,
            subject_id=subject_id,
            monitor_id=monitor_id,
        )
        if monitor is None:
            raise KeyError("monitor not found")
        return monitor

    def apply_capture(
        self,
        *,
        monitor: Monitor,
        job: Job,
        extracted_text: str,
        observed_at: datetime.datetime,
    ) -> MonitorRunResult:
        if job.tenant_id != monitor.tenant_id or job.subject_id != monitor.subject_id:
            raise PermissionError("monitor run scope does not match the monitor")
        if job.payload.get("monitor_id") != monitor.monitor_id:
            raise ValueError("monitor run references a different monitor")
        expected_version = job.payload.get("baseline_version")
        if not isinstance(expected_version, int) or isinstance(expected_version, bool):
            raise ValueError("monitor run has an invalid baseline version")
        if observed_at.tzinfo is None or observed_at.utcoffset() is None:
            raise ValueError("monitor observation time must be timezone-aware")
        if observed_at > datetime.datetime.now(datetime.UTC):
            raise BaselineConflictError("monitor capture time is in the future")
        if (
            monitor.baseline_observed_at is not None
            and observed_at <= monitor.baseline_observed_at
        ):
            raise BaselineConflictError("monitor capture is older than the successful baseline")
        digest = normalize_text_digest(extracted_text)
        previous = monitor.baseline_digest
        result = MonitorRunResult(
            monitor_id=monitor.monitor_id,
            job_id=job.job_id,
            status=MonitorRunStatus.SUCCEEDED,
            previous_digest=previous,
            current_digest=digest,
            changed=None if previous is None else previous != digest,
            observed_at=observed_at,
            changed_units=int(previous is not None and previous != digest),
        )
        self.repository.commit_successful_run(
            tenant_id=monitor.tenant_id,
            subject_id=monitor.subject_id,
            monitor_id=monitor.monitor_id,
            expected_baseline_version=expected_version,
            result=result,
        )
        return result

    async def execute(self, job: Job) -> dict[str, Any]:
        """Acquire and persist a single leased run without exposing page content."""
        if self.acquisition is None:
            raise RuntimeError("monitor acquisition is not configured")
        monitor_id = job.payload.get("monitor_id")
        if not isinstance(monitor_id, str):
            raise ValueError("monitor job is missing its monitor ID")
        monitor = self.repository.get(
            tenant_id=job.tenant_id,
            subject_id=job.subject_id,
            monitor_id=monitor_id,
        )
        if monitor is None:
            raise KeyError("monitor not found")
        max_bytes = monitor.policy.get("max_bytes")
        page = await self.acquisition.acquire_page(
            monitor.target_url,
            tenant_id=job.tenant_id,
            max_bytes=max_bytes if isinstance(max_bytes, int) else None,
        )
        try:
            result = self.apply_capture(
                monitor=monitor,
                job=job,
                extracted_text=page.extracted.text,
                observed_at=page.fetch.retrieved_at,
            )
        except BaselineConflictError:
            return {"outcome": "stale_capture", "monitor_id": monitor.monitor_id}
        outcome = (
            "baseline_established"
            if result.previous_digest is None
            else "changed"
            if result.changed
            else "unchanged"
        )
        return {
            "outcome": outcome,
            "monitor_id": result.monitor_id,
            "job_id": result.job_id,
            "previous_digest": result.previous_digest,
            "current_digest": result.current_digest,
            "changed": result.changed,
            "changed_units": result.changed_units,
            "observed_at": result.observed_at.isoformat(),
            "artifact_id": page.artifact_id,
        }
