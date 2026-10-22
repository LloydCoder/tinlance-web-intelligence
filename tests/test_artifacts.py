from datetime import UTC, datetime, timedelta

import pytest

from tinlance_web_intelligence.artifacts.store import MemoryArtifactStore


def test_content_is_deduplicated_but_source_capture_records_are_preserved() -> None:
    store = MemoryArtifactStore()
    now = datetime(2026, 10, 18, tzinfo=UTC)
    first = store.put(
        body=b"same content", content_type="text/html", source_url="https://one.example/",
        captured_at=now,
    )
    second = store.put(
        body=b"same content", content_type="text/html", source_url="https://two.example/",
        captured_at=now,
    )
    assert first.sha256 == second.sha256
    assert first.artifact_id == second.artifact_id
    assert first.source_url != second.source_url
    assert store.get(first.sha256) == b"same content"
    assert store.count() == 2


def test_artifact_source_url_query_strings_are_not_retained() -> None:
    store = MemoryArtifactStore()
    record = store.put(
        body=b"private query response",
        content_type="text/html",
        source_url="https://example.com/search?token=secret-token&q=private+search",
        captured_at=datetime(2026, 10, 18, tzinfo=UTC),
    )

    assert record.source_url == "https://example.com/search"
    assert "secret-token" not in record.source_url
    assert "private+search" not in record.source_url


def test_memory_artifacts_are_tenant_scoped() -> None:
    store = MemoryArtifactStore()
    now = datetime(2026, 10, 18, tzinfo=UTC)
    record = store.put(
        body=b"tenant-private bytes",
        content_type="text/html",
        source_url="https://private.example/",
        captured_at=now,
        tenant_id="tenant-a",
    )
    assert store.get(record.sha256, tenant_id="tenant-a") == b"tenant-private bytes"
    assert store.get(record.sha256, tenant_id="tenant-b") is None
    assert store.count(tenant_id="tenant-a") == 1
    assert store.count(tenant_id="tenant-b") == 0


def test_artifact_retention_prunes_only_expired_capture_records() -> None:
    store = MemoryArtifactStore()
    now = datetime(2026, 10, 18, tzinfo=UTC)
    old = store.put(
        body=b"shared content", content_type="text/html", source_url="https://one.example/",
        captured_at=now - timedelta(days=45), tenant_id="tenant-a",
    )
    store.put(
        body=b"shared content", content_type="text/html", source_url="https://one.example/",
        captured_at=now, tenant_id="tenant-a",
    )
    cutoff = now - timedelta(days=30)
    assert store.count_expired(cutoff, tenant_id="tenant-a") == 1
    assert store.prune_before(cutoff, tenant_id="tenant-a") == 1
    assert store.count(tenant_id="tenant-a") == 1
    assert store.get(old.sha256, tenant_id="tenant-a") == b"shared content"

def test_artifact_store_rejects_malformed_digest_and_source_metadata() -> None:
    store = MemoryArtifactStore()
    with pytest.raises(ValueError, match="SHA-256"):
        store.get("a" * 64 + "suffix")
    now = datetime(2026, 10, 18, tzinfo=UTC)
    with pytest.raises(ValueError, match="absolute HTTP"):
        store.put(
            body=b"body",
            content_type="text/html",
            source_url="file:///etc/passwd",
            captured_at=now,
        )
    with pytest.raises(ValueError, match="userinfo"):
        store.put(
            body=b"body",
            content_type="text/html",
            source_url="https://user:password@example.com/",
            captured_at=now,
        )
    with pytest.raises(ValueError, match="content_type"):
        store.put(
            body=b"body",
            content_type="text/html" + chr(10) + "X-Injected: true",
            source_url="https://example.com/",
            captured_at=now,
        )

