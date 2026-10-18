from __future__ import annotations

import base64

import pytest

from tinlance_web_intelligence.security.egress_proxy import (
    EgressProxyConfig,
    ProxyAuthenticationError,
    ProxyPolicyError,
    ProxyProtocolError,
    SafeEgressProxy,
)

TEST_PROXY_PASSWORD = "correct-horse-battery-staple-2026"


def make_proxy() -> SafeEgressProxy:
    return SafeEgressProxy(EgressProxyConfig(
        host="127.0.0.1",
        port=3128,
        username="browser-worker",
        password=TEST_PROXY_PASSWORD,
    ))


def test_proxy_rejects_weak_secrets_and_invalid_limits() -> None:
    with pytest.raises(ValueError):
        EgressProxyConfig(host="127.0.0.1", port=3128, username="worker", password="weak").validate()
    with pytest.raises(ValueError):
        EgressProxyConfig(host="127.0.0.1", port=70000, username="worker", password=TEST_PROXY_PASSWORD).validate()


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
    assert SafeEgressProxy._parse_target("CONNECT", "example.com:443") == ("example.com", 443)
