from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

from tinlance_web_intelligence.jobs.repository import SQLiteJobRepository


def test_w3_database_migrates_to_browser_job_kind_without_losing_jobs(tmp_path: Path) -> None:
    path = tmp_path / "w3.sqlite3"
    connection = sqlite3.connect(path)
    connection.execute(
        """CREATE TABLE jobs (
            job_id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            subject_id TEXT NOT NULL,
            kind TEXT NOT NULL CHECK (kind IN ('search', 'fetch')),
            payload_json TEXT NOT NULL,
            payload_fingerprint TEXT NOT NULL,
            status TEXT NOT NULL CHECK (
                status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')
            ),
            result_json TEXT,
            error_code TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            attempts INTEGER NOT NULL DEFAULT 0,
            max_attempts INTEGER NOT NULL DEFAULT 3,
            available_at REAL NOT NULL,
            lease_owner TEXT,
            lease_until REAL,
            cancel_requested INTEGER NOT NULL DEFAULT 0,
            idempotency_key TEXT NOT NULL,
            UNIQUE (tenant_id, subject_id, idempotency_key)
        )"""
    )
    connection.execute(
        "INSERT INTO jobs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "legacy-job", "tenant-a", "subject-a", "search",
            json.dumps({"query": "legacy", "limit": 1}), "a" * 64,
            "queued", None, None, "2026-01-01T00:00:00+00:00",
            "2026-01-01T00:00:00+00:00", 0, 3, time.time(),
            None, None, 0, "legacy-request-key-0001",
        ),
    )
    connection.execute("CREATE INDEX jobs_claim_idx ON jobs(status, available_at, created_at)")
    connection.execute("CREATE INDEX jobs_tenant_idx ON jobs(tenant_id, subject_id, created_at)")
    connection.commit()
    connection.close()

    repository = SQLiteJobRepository(str(path))
    legacy = repository.get("legacy-job", tenant_id="tenant-a", subject_id="subject-a")
    assert legacy is not None
    assert legacy.payload == {"query": "legacy", "limit": 1}
    browser = repository.create(
        tenant_id="tenant-a",
        subject_id="subject-a",
        kind="browser",
        payload={"url": "https://example.com/", "wait_until": "load",
                 "timeout_ms": 10000, "include_screenshot": False},
        idempotency_key="browser-request-key-0001",
    )
    assert browser.kind == "browser"
    monitor = repository.create(
        tenant_id="tenant-a",
        subject_id="subject-a",
        kind="monitor",
        payload={"monitor_id": "monitor-1", "baseline_version": 0},
        idempotency_key="monitor-run-key-0001",
        traceparent="00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
    )
    assert monitor.kind == "monitor"
    assert monitor.traceparent is not None
    repository.close()
