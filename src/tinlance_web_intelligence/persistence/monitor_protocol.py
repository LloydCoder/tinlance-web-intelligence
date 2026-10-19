"""Persistence interface for tenant-scoped monitor lifecycle state."""

from __future__ import annotations

from typing import Protocol

from tinlance_web_intelligence.monitors.model import Monitor, MonitorRunResult


class MonitorRepository(Protocol):
    def create(
        self,
        *,
        tenant_id: str,
        subject_id: str,
        target_url: str,
        policy: dict[str, object],
        idempotency_key: str,
    ) -> Monitor: ...

    def get(
        self,
        *,
        tenant_id: str,
        subject_id: str | None,
        monitor_id: str,
        administrative: bool = False,
    ) -> Monitor | None: ...

    def set_status(
        self,
        *,
        tenant_id: str,
        subject_id: str,
        monitor_id: str,
        status: str,
    ) -> Monitor | None: ...

    def commit_successful_run(
        self,
        *,
        tenant_id: str,
        subject_id: str,
        monitor_id: str,
        expected_baseline_version: int,
        result: MonitorRunResult,
    ) -> Monitor: ...

    def record_run_result(self, result: MonitorRunResult) -> None: ...

    def metrics_snapshot(self) -> dict[str, float]: ...

    def ping(self) -> bool: ...

    def close(self) -> None: ...

