"""Unit tests for the process-local PostgreSQL pool registry."""
from __future__ import annotations

from collections.abc import Generator
from typing import Any

import pytest

from tinlance_web_intelligence.persistence import postgres_pool


class _FakePool:
    created: list[_FakePool] = []

    def __class_getitem__(cls, _item: object) -> type[_FakePool]:
        return cls

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs
        self.waited = False
        self.closed = False
        self.created.append(self)

    def wait(self, *, timeout: float) -> None:
        assert timeout == 10
        self.waited = True

    def close(self) -> None:
        self.closed = True


@pytest.fixture(autouse=True)
def reset_registry(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    with postgres_pool._lock:
        postgres_pool._pools.clear()
    _FakePool.created.clear()
    monkeypatch.setattr(postgres_pool, "ConnectionPool", _FakePool)
    yield
    with postgres_pool._lock:
        postgres_pool._pools.clear()


def test_pool_is_shared_until_every_adapter_releases_it() -> None:
    first = postgres_pool.acquire_pool("postgresql://user:secret@db.example/app")
    second = postgres_pool.acquire_pool("postgresql://user:secret@db.example/app")

    assert first is second
    assert len(_FakePool.created) == 1
    assert postgres_pool.pool_registry_snapshot() == {
        "pools": 1,
        "references": 2,
        "max_connections": 10,
    }

    postgres_pool.release_pool(first)
    assert not _FakePool.created[0].closed
    postgres_pool.release_pool(second)
    assert _FakePool.created[0].closed
    assert postgres_pool.pool_registry_snapshot() == {
        "pools": 0,
        "references": 0,
        "max_connections": 0,
    }


def test_shared_pool_rejects_conflicting_size_configuration() -> None:
    pool = postgres_pool.acquire_pool("postgresql://db.example/app", max_size=8)
    with pytest.raises(ValueError, match="identical pool sizing"):
        postgres_pool.acquire_pool("postgresql://db.example/app", max_size=10)
    postgres_pool.release_pool(pool)


def test_registry_snapshot_never_exposes_connection_strings() -> None:
    pool = postgres_pool.acquire_pool("postgresql://user:secret@db.example/app")
    snapshot = str(postgres_pool.pool_registry_snapshot())
    assert "secret" not in snapshot
    assert "db.example" not in snapshot
    postgres_pool.release_pool(pool)
