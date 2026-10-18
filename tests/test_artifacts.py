from datetime import UTC, datetime

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
