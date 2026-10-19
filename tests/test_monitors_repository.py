from __future__ import annotations

from datetime import UTC, datetime

import pytest

from tinlance_web_intelligence.monitors.model import (
    IdempotencyConflictError,
    MonitorRunResult,
    MonitorRunStatus,
)
from tinlance_web_intelligence.persistence.sqlite_monitors import SQLiteMonitorRepository


def test_create_is_idempotent_and_scoped_to_tenant_subject(tmp_path) -> None:
    repository = SQLiteMonitorRepository(str(tmp_path / "monitors.sqlite3"))
    try:
        created = repository.create(
            tenant_id="tenant-a",
            subject_id="subject-a",
            target_url="https://example.test/path?secret=value",
            policy={"max_bytes": 4096},
            idempotency_key="create-1",
        )

        replay = repository.create(
            tenant_id="tenant-a",
            subject_id="subject-a",
            target_url="https://example.test/path?secret=value",
            policy={"max_bytes": 4096},
            idempotency_key="create-1",
        )

        assert replay.monitor_id == created.monitor_id
        assert repository.get(
            tenant_id="tenant-b", subject_id="subject-a", monitor_id=created.monitor_id
        ) is None
        assert repository.get(
            tenant_id="tenant-a", subject_id="subject-b", monitor_id=created.monitor_id
        ) is None
    finally:
        repository.close()


def test_create_rejects_idempotency_key_reuse_for_different_payload(tmp_path) -> None:
    repository = SQLiteMonitorRepository(str(tmp_path / "monitors.sqlite3"))
    try:
        repository.create(
            tenant_id="tenant-a",
            subject_id="subject-a",
            target_url="https://example.test/one",
            policy={},
            idempotency_key="create-1",
        )

        with pytest.raises(IdempotencyConflictError):
            repository.create(
                tenant_id="tenant-a",
                subject_id="subject-a",
                target_url="https://example.test/two",
                policy={},
                idempotency_key="create-1",
            )
    finally:
        repository.close()


def test_only_successful_expected_version_run_advances_baseline(tmp_path) -> None:
    repository = SQLiteMonitorRepository(str(tmp_path / "monitors.sqlite3"))
    try:
        monitor = repository.create(
            tenant_id="tenant-a",
            subject_id="subject-a",
            target_url="https://example.test/",
            policy={},
            idempotency_key="create-1",
        )
        observed_at = datetime(2026, 10, 19, tzinfo=UTC)
        result = MonitorRunResult(
            monitor_id=monitor.monitor_id,
            job_id="job-1",
            status=MonitorRunStatus.SUCCEEDED,
            previous_digest=None,
            current_digest="a" * 64,
            changed=None,
            observed_at=observed_at,
            changed_units=0,
        )

        updated = repository.commit_successful_run(
            tenant_id="tenant-a",
            subject_id="subject-a",
            monitor_id=monitor.monitor_id,
            expected_baseline_version=0,
            result=result,
        )

        assert updated.baseline_digest == "a" * 64
        assert updated.baseline_version == 1
        assert repository.record_run_result(result) is None
    finally:
        repository.close()
