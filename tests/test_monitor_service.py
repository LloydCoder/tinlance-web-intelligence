from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

from tinlance_web_intelligence.jobs.model import Job, JobStatus
from tinlance_web_intelligence.monitors.model import BaselineConflictError
from tinlance_web_intelligence.monitors.service import MonitorService
from tinlance_web_intelligence.persistence.sqlite_monitors import SQLiteMonitorRepository


def _running_job(monitor_id: str, version: int, job_id: str) -> Job:
    timestamp = datetime(2026, 10, 19, tzinfo=UTC).isoformat()
    return Job(
        job_id=job_id,
        tenant_id="tenant-a",
        subject_id="subject-a",
        kind="monitor",
        payload={"monitor_id": monitor_id, "baseline_version": version},
        status=JobStatus.RUNNING,
        created_at=timestamp,
        updated_at=timestamp,
        attempts=1,
        max_attempts=3,
    )


def test_first_capture_establishes_normalized_baseline(tmp_path: Path) -> None:
    repository = SQLiteMonitorRepository(str(tmp_path / "monitors.sqlite3"))
    monitor = repository.create(
        tenant_id="tenant-a",
        subject_id="subject-a",
        target_url="https://example.test/",
        policy={},
        idempotency_key="monitor-1",
    )
    service = MonitorService(repository=repository)

    result = service.apply_capture(
        monitor=monitor,
        job=_running_job(monitor.monitor_id, 0, "job-1"),
        extracted_text="  Ｈi\n   there  ",
        observed_at=datetime(2026, 10, 19, tzinfo=UTC),
    )

    assert result.changed is None
    assert result.current_digest is not None
    updated = repository.get(
        tenant_id="tenant-a", subject_id="subject-a", monitor_id=monitor.monitor_id
    )
    assert updated is not None and updated.baseline_version == 1
    repository.close()


def test_reformatted_equivalent_text_does_not_report_a_change(tmp_path: Path) -> None:
    repository = SQLiteMonitorRepository(str(tmp_path / "monitors.sqlite3"))
    monitor = repository.create(
        tenant_id="tenant-a",
        subject_id="subject-a",
        target_url="https://example.test/",
        policy={},
        idempotency_key="monitor-1",
    )
    service = MonitorService(repository=repository)
    service.apply_capture(
        monitor=monitor,
        job=_running_job(monitor.monitor_id, 0, "job-1"),
        extracted_text="  Ｈi\n   there  ",
        observed_at=datetime(2026, 10, 19, tzinfo=UTC),
    )
    updated = repository.get(
        tenant_id="tenant-a", subject_id="subject-a", monitor_id=monitor.monitor_id
    )
    assert updated is not None

    result = service.apply_capture(
        monitor=updated,
        job=_running_job(monitor.monitor_id, 1, "job-2"),
        extracted_text="Hi there",
        observed_at=datetime(2026, 10, 19, 1, tzinfo=UTC),
    )

    assert result.changed is False
    assert result.changed_units == 0
    repository.close()


def test_stale_capture_cannot_overwrite_newer_baseline(tmp_path: Path) -> None:
    repository = SQLiteMonitorRepository(str(tmp_path / "monitors.sqlite3"))
    monitor = repository.create(
        tenant_id="tenant-a",
        subject_id="subject-a",
        target_url="https://example.test/",
        policy={},
        idempotency_key="monitor-1",
    )
    service = MonitorService(repository=repository)
    service.apply_capture(
        monitor=monitor,
        job=_running_job(monitor.monitor_id, 0, "job-1"),
        extracted_text="first",
        observed_at=datetime(2026, 10, 19, tzinfo=UTC),
    )
    updated = repository.get(
        tenant_id="tenant-a", subject_id="subject-a", monitor_id=monitor.monitor_id
    )
    assert updated is not None

    with pytest.raises(BaselineConflictError):
        service.apply_capture(
            monitor=updated,
            job=_running_job(monitor.monitor_id, 0, "job-stale"),
            extracted_text="stale result",
            observed_at=datetime(2026, 10, 19, 2, tzinfo=UTC),
        )

    after = repository.get(
        tenant_id="tenant-a", subject_id="subject-a", monitor_id=monitor.monitor_id
    )
    assert after is not None
    assert after.baseline_digest == updated.baseline_digest
    assert after.baseline_version == updated.baseline_version
    repository.close()


def test_future_capture_cannot_advance_baseline(tmp_path: Path) -> None:
    repository = SQLiteMonitorRepository(str(tmp_path / "monitors.sqlite3"))
    monitor = repository.create(
        tenant_id="tenant-a",
        subject_id="subject-a",
        target_url="https://example.test/",
        policy={},
        idempotency_key="monitor-1",
    )
    service = MonitorService(repository=repository)

    with pytest.raises(BaselineConflictError):
        service.apply_capture(
            monitor=monitor,
            job=_running_job(monitor.monitor_id, 0, "future-job"),
            extracted_text="future",
            observed_at=datetime(2027, 1, 1, tzinfo=UTC),
        )

    current = repository.get(
        tenant_id="tenant-a", subject_id="subject-a", monitor_id=monitor.monitor_id
    )
    assert current is not None and current.baseline_version == 0
    repository.close()


def test_pause_does_not_revoke_an_already_leased_run(tmp_path: Path) -> None:
    repository = SQLiteMonitorRepository(str(tmp_path / "monitors.sqlite3"))
    monitor = repository.create(
        tenant_id="tenant-a",
        subject_id="subject-a",
        target_url="https://example.test/",
        policy={},
        idempotency_key="monitor-1",
    )

    class Acquisition:
        async def acquire_page(
            self, url: str, *, tenant_id: str, max_bytes: int | None = None
        ) -> Any:
            del url, tenant_id, max_bytes
            fetched = SimpleNamespace(retrieved_at=datetime(2026, 10, 19, 1, tzinfo=UTC))
            extracted = SimpleNamespace(text="leased capture")
            return SimpleNamespace(
                fetch=fetched,
                extracted=extracted,
                artifact_id="sha256:" + "a" * 64,
            )

    service = MonitorService(
        repository=repository,
        acquisition=cast(Any, Acquisition()),
    )
    service.pause(tenant_id="tenant-a", subject_id="subject-a", monitor_id=monitor.monitor_id)
    result = asyncio.run(
        service.execute(_running_job(monitor.monitor_id, 0, "leased-run"))
    )

    assert result["outcome"] == "baseline_established"
    updated = repository.get(
        tenant_id="tenant-a", subject_id="subject-a", monitor_id=monitor.monitor_id
    )
    assert updated is not None and updated.baseline_version == 1
    repository.close()


def test_monitor_execution_applies_stored_response_byte_bound(tmp_path: Path) -> None:
    repository = SQLiteMonitorRepository(str(tmp_path / "monitors.sqlite3"))
    monitor = repository.create(
        tenant_id="tenant-a",
        subject_id="subject-a",
        target_url="https://example.test/",
        policy={"max_bytes": 1024},
        idempotency_key="monitor-1",
    )

    class Acquisition:
        max_bytes: int | None = None

        async def acquire_page(
            self, url: str, *, tenant_id: str, max_bytes: int | None = None
        ) -> Any:
            del url, tenant_id
            self.max_bytes = max_bytes
            fetched = SimpleNamespace(retrieved_at=datetime(2026, 10, 19, 1, tzinfo=UTC))
            extracted = SimpleNamespace(text="bounded capture")
            return SimpleNamespace(
                fetch=fetched,
                extracted=extracted,
                artifact_id="sha256:" + "b" * 64,
            )

    acquisition = Acquisition()
    service = MonitorService(repository=repository, acquisition=cast(Any, acquisition))
    asyncio.run(service.execute(_running_job(monitor.monitor_id, 0, "bounded-run")))

    assert acquisition.max_bytes == 1024
    repository.close()
