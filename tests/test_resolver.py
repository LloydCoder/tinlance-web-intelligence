import asyncio
import socket
from typing import Any

import pytest

from tinlance_web_intelligence.security.resolver import PublicOnlyResolver
from tinlance_web_intelligence.security.url_validation import UnsafeURLError


class FakeResolver:
    def __init__(self, addresses: list[str]) -> None:
        self.addresses = addresses
        self.closed = False

    async def resolve(
        self, host: str, port: int = 0, family: int = socket.AF_INET
    ) -> list[dict[str, Any]]:
        return [
            {
                "hostname": host,
                "host": address,
                "port": port,
                "family": family,
                "proto": 0,
                "flags": 0,
            }
            for address in self.addresses
        ]

    async def close(self) -> None:
        self.closed = True


def test_resolver_accepts_only_public_dns_answers() -> None:
    resolver = PublicOnlyResolver(FakeResolver(["1.1.1.1"]))  # type: ignore[arg-type]
    result = asyncio.run(resolver.resolve("example.com", 443, socket.AF_INET))
    assert result[0]["host"] == "1.1.1.1"


@pytest.mark.parametrize(
    "address",
    ["127.0.0.1", "10.0.0.2", "169.254.169.254", "::1", "fd00::1"],
)
def test_resolver_rejects_any_non_public_dns_answer(address: str) -> None:
    resolver = PublicOnlyResolver(FakeResolver(["1.1.1.1", address]))  # type: ignore[arg-type]
    with pytest.raises(UnsafeURLError):
        asyncio.run(resolver.resolve("attacker.example", 443, socket.AF_INET))
