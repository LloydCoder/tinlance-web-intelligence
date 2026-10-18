"""Syntactic URL validation and IP classification for SSRF-resistant acquisition.

This module is a first gate only. Callers must also validate DNS answers at connection
time, revalidate every redirect, and enforce network egress restrictions.
"""

from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit


class UnsafeURLError(ValueError):
    """Raised when a URL violates acquisition policy."""


@dataclass(frozen=True, slots=True)
class ValidatedURL:
    normalized: str
    scheme: str
    hostname: str
    port: int | None


def is_public_routable_ip(value: str) -> bool:
    """Return True only for globally routable unicast addresses."""
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return False
    blocked = (
        address.is_loopback,
        address.is_private,
        address.is_link_local,
        address.is_multicast,
        address.is_reserved,
        address.is_unspecified,
    )
    return address.is_global and not any(blocked)


def _legacy_ipv4_literal(hostname: str) -> ipaddress.IPv4Address | None:
    """Recognize legacy inet_aton forms such as integer, octal, and short IPv4 forms."""
    try:
        packed = socket.inet_aton(hostname)
    except OSError:
        return None
    return ipaddress.IPv4Address(packed)


def validate_url(
    value: str, *, allowed_schemes: tuple[str, ...] = ("https", "http")
) -> ValidatedURL:
    if (
        not value
        or value != value.strip()
        or "\\" in value
        or any(ord(ch) < 32 for ch in value)
    ):
        raise UnsafeURLError(
            "URL must be trimmed, contain no backslashes, and contain no control characters"
        )
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as exc:
        raise UnsafeURLError("malformed URL or invalid port") from exc
    scheme = parsed.scheme.lower()
    if scheme not in allowed_schemes or scheme not in {"http", "https"}:
        raise UnsafeURLError("URL scheme is not allowed")
    if not parsed.hostname:
        raise UnsafeURLError("URL must include a hostname")
    if parsed.username is not None or parsed.password is not None:
        raise UnsafeURLError("URL userinfo is forbidden")
    if parsed.fragment:
        raise UnsafeURLError("URL fragments are forbidden for canonical acquisition requests")
    hostname = parsed.hostname.rstrip(".").lower()
    if not hostname or hostname == "localhost" or hostname.endswith(".localhost"):
        raise UnsafeURLError("localhost destinations are forbidden")
    if hostname.endswith(".local") or hostname.endswith(".internal"):
        raise UnsafeURLError("local and internal DNS namespaces are forbidden")
    try:
        literal = ipaddress.ip_address(hostname)
    except ValueError:
        literal = _legacy_ipv4_literal(hostname)
    if literal is not None and not is_public_routable_ip(str(literal)):
        raise UnsafeURLError("non-public IP destinations are forbidden")
    if port is not None and not 1 <= port <= 65535:
        raise UnsafeURLError("port is outside the valid range")
    netloc = f"[{hostname}]" if ":" in hostname else hostname
    if port is not None:
        netloc = f"{netloc}:{port}"
    normalized = urlunsplit((scheme, netloc, parsed.path or "/", parsed.query, ""))
    return ValidatedURL(normalized, scheme, hostname, port)
