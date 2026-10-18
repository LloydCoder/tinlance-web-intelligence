"""Connection-time DNS filtering for public web acquisition."""

from __future__ import annotations

import socket
from typing import Any

from aiohttp.abc import AbstractResolver
from aiohttp.resolver import DefaultResolver

from tinlance_web_intelligence.security.url_validation import UnsafeURLError, is_public_routable_ip


class PublicOnlyResolver(AbstractResolver):
    """Reject DNS answers containing any non-public address.

    aiohttp connects to one of the addresses returned by this resolver, so validation
    is performed in the same lookup used by the connector rather than in a separate,
    racy preflight lookup. Network-level egress restrictions remain mandatory.
    """

    def __init__(self, delegate: AbstractResolver | None = None) -> None:
        self._delegate = delegate or DefaultResolver()

    async def resolve(
        self, host: str, port: int = 0, family: int = socket.AF_INET
    ) -> list[dict[str, Any]]:
        results = await self._delegate.resolve(host, port, family)
        if not results:
            raise UnsafeURLError("destination has no DNS addresses")
        for result in results:
            address = str(result.get("host", ""))
            if not is_public_routable_ip(address):
                raise UnsafeURLError("destination resolved to a non-public IP address")
        return results

    async def close(self) -> None:
        await self._delegate.close()
