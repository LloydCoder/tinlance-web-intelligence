"""Process-local, reference-counted PostgreSQL connection-pool registry.

One pool is shared by persistence adapters that use the same DSN and sizing.
This bounds database connections per process instead of multiplying a full pool
for every repository. DSNs are used only as in-memory registry keys and are
never emitted in logs or metrics.
"""
from __future__ import annotations

import threading
from typing import Any

from psycopg import Connection
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

Pool = ConnectionPool[Connection[dict[str, Any]]]


class _PoolEntry:
    def __init__(self, pool: Pool, min_size: int, max_size: int) -> None:
        self.pool = pool
        self.min_size = min_size
        self.max_size = max_size
        self.references = 1


_lock = threading.RLock()
_pools: dict[str, _PoolEntry] = {}


def acquire_pool(dsn: str, *, min_size: int = 1, max_size: int = 10) -> Pool:
    """Acquire a shared pool for a DSN, rejecting conflicting sizing requests."""
    if not dsn or dsn != dsn.strip():
        raise ValueError("PostgreSQL DSN must be non-empty and normalized")
    if not 1 <= min_size <= max_size <= 50:
        raise ValueError("invalid PostgreSQL pool configuration")
    with _lock:
        entry = _pools.get(dsn)
        if entry is not None:
            if (entry.min_size, entry.max_size) != (min_size, max_size):
                raise ValueError(
                    "PostgreSQL adapters sharing a DSN must use identical pool sizing"
                )
            entry.references += 1
            return entry.pool
        pool = ConnectionPool[Connection[dict[str, Any]]](
            conninfo=dsn,
            min_size=min_size,
            max_size=max_size,
            kwargs={"row_factory": dict_row, "connect_timeout": 5},
            timeout=10,
            open=True,
        )
        try:
            pool.wait(timeout=10)
        except Exception:
            pool.close()
            raise
        _pools[dsn] = _PoolEntry(pool, min_size, max_size)
        return pool


def release_pool(pool: Pool) -> None:
    """Release one adapter's reference; close the underlying pool at zero."""
    to_close: Pool | None = None
    with _lock:
        for dsn, entry in tuple(_pools.items()):
            if entry.pool is pool:
                entry.references -= 1
                if entry.references <= 0:
                    del _pools[dsn]
                    to_close = pool
                break
        else:
            # A pool not owned by this registry is not ours to close.
            return
    if to_close is not None:
        to_close.close()


def pool_registry_snapshot() -> dict[str, int]:
    """Expose only aggregate pool counts for diagnostics; never expose DSNs."""
    with _lock:
        return {
            "pools": len(_pools),
            "references": sum(entry.references for entry in _pools.values()),
            "max_connections": sum(entry.max_size for entry in _pools.values()),
        }
