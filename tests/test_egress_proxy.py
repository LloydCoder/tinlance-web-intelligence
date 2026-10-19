from __future__ import annotations

import asyncio
import base64
import secrets
import socket

import pytest

from tinlance_web_intelligence.security.egress_proxy import (
    EgressProxyConfig,
    ProxyAuthenticationError,
    ProxyPolicyError,
    ProxyProtocolError,
    SafeEgressProxy,
)

TEST_CREDENTIAL = secrets.token_urlsafe(32)


def make_proxy() -> SafeEgressProxy:
    return SafeEgressProxy(EgressProxyConfig(
        host="127.0.0.1",
        port=3128,
        username="browser-worker",
        password=TEST_CREDENTIAL,
    ))


def test_proxy_rejects_weak_secrets_and_invalid_limits() -> None:
    with pytest.raises(ValueError):
        weak_value = "weak"
        EgressProxyConfig(
            host="127.0.0.1", port=3128, username="worker", password=weak_value
        ).validate()
    with pytest.raises(ValueError):
        EgressProxyConfig(
            host="127.0.0.1",
            port=70000,
            username="worker",
            password=TEST_CREDENTIAL,
        ).validate()
    with pytest.raises(ValueError):
        EgressProxyConfig(
            host="192.0.2.10",
            port=3128,
            username="worker",
            password=TEST_CREDENTIAL,
        ).validate()
    with pytest.raises(ValueError):
        EgressProxyConfig(
            host="egress-proxy.example.com",
            port=3128,
            username="worker",
            password=TEST_CREDENTIAL,
        ).validate()


def test_proxy_authentication_requires_exact_single_basic_credential() -> None:
    instance = make_proxy()
    encoded = base64.b64encode(
        f"{instance.config.username}:{instance.config.password}".encode()
    ).decode("ascii")
    instance._authenticate([("Proxy-Authorization", f"Basic {encoded}")])
    with pytest.raises(ProxyAuthenticationError):
        instance._authenticate([])
    with pytest.raises(ProxyAuthenticationError):
        instance._authenticate([
            ("Proxy-Authorization", f"Basic {encoded}"),
            ("Proxy-Authorization", f"Basic {encoded}"),
        ])


def test_proxy_protocol_and_destination_policy_fail_closed() -> None:
    with pytest.raises(ProxyProtocolError):
        SafeEgressProxy._parse_request(b"GET / HTTP/1.1\r\n\r\n")
    with pytest.raises(ProxyProtocolError):
        SafeEgressProxy._parse_request(b"POST http://example.com/ HTTP/1.1\r\n\r\n")
    with pytest.raises(ProxyPolicyError):
        SafeEgressProxy._parse_target("CONNECT", "example.com:80")
    with pytest.raises(ProxyPolicyError):
        SafeEgressProxy._parse_target("GET", "http://example.com:8080/")
    assert SafeEgressProxy._parse_target("CONNECT", "example.com:443") == (
        "example.com",
        443,
    )
    assert SafeEgressProxy._parse_target(
        "CONNECT", "[2606:4700:4700::1111]:443"
    ) == ("2606:4700:4700::1111", 443)


def test_proxy_rejects_non_public_ip_literals() -> None:
    async def check() -> None:
        proxy = make_proxy()
        for address in (
            "127.0.0.1",
            "10.0.0.1",
            "169.254.169.254",
            "192.0.2.1",
            "198.18.0.1",
            "240.0.0.1",
            "::1",
            "fc00::1",
            "2001:db8::1",
        ):
            with pytest.raises(ProxyPolicyError):
                await proxy._resolve_public_ip(address, 443, "https")
        assert await proxy._resolve_public_ip("8.8.8.8", 443, "https") == "8.8.8.8"
        with pytest.raises(ProxyPolicyError):
            await proxy._resolve_public_ip("8.8.8.8", 80, "https")

    asyncio.run(check())


def test_proxy_rejects_empty_dns_answers(monkeypatch: pytest.MonkeyPatch) -> None:
    async def check() -> None:
        loop = asyncio.get_running_loop()

        async def empty_getaddrinfo(
            host: str, port: int, *, type: int
        ) -> list[tuple[object, ...]]:
            return []

        monkeypatch.setattr(loop, "getaddrinfo", empty_getaddrinfo)
        with pytest.raises(ProxyPolicyError, match="no addresses"):
            await make_proxy()._resolve_public_ip("empty.example", 443, "https")

    asyncio.run(check())


@pytest.mark.parametrize(
    "addresses",
    [
        ["1.1.1.1", "127.0.0.1"],
        ["8.8.8.8", "169.254.169.254"],
        ["1.1.1.1", "10.0.0.1"],
        ["1.1.1.1", "fd00::1"],
    ],
)
def test_proxy_rejects_mixed_public_and_non_public_dns_answers(
    monkeypatch: pytest.MonkeyPatch, addresses: list[str]
) -> None:
    async def check() -> None:
        loop = asyncio.get_running_loop()

        async def fake_getaddrinfo(
            host: str, port: int, *, type: int
        ) -> list[tuple[object, ...]]:
            results = []
            for address in addresses:
                family = socket.AF_INET6 if ":" in address else socket.AF_INET
                results.append((family, 1, 6, "", (address, port)))
            return results

        monkeypatch.setattr(loop, "getaddrinfo", fake_getaddrinfo)
        with pytest.raises(ProxyPolicyError, match="non-public address"):
            await make_proxy()._resolve_public_ip("rebinding.example", 443, "https")

    asyncio.run(check())


def test_proxy_resolves_and_returns_one_validated_ip_for_connection_pinning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def check() -> None:
        loop = asyncio.get_running_loop()
        calls = 0

        async def fake_getaddrinfo(
            host: str, port: int, *, type: int
        ) -> list[tuple[object, ...]]:
            nonlocal calls
            calls += 1
            return [
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", port)),
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("1.1.1.1", port)),
            ]

        monkeypatch.setattr(loop, "getaddrinfo", fake_getaddrinfo)
        result = await make_proxy()._resolve_public_ip("public.example", 443, "https")
        assert result == "1.1.1.1"
        assert calls == 1

    asyncio.run(check())
