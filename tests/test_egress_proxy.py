from __future__ import annotations

import asyncio
import base64
import secrets

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
        for address in ("127.0.0.1", "10.0.0.1", "169.254.169.254", "::1", "fc00::1"):
            with pytest.raises(ProxyPolicyError):
                await proxy._resolve_public_ip(address, 443, "https")
        assert await proxy._resolve_public_ip("8.8.8.8", 443, "https") == "8.8.8.8"
        with pytest.raises(ProxyPolicyError):
            await proxy._resolve_public_ip("8.8.8.8", 80, "https")

    asyncio.run(check())
