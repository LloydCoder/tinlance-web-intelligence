"""Strict request validation for public-web browser acquisition."""

from __future__ import annotations

import ipaddress
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from tinlance_web_intelligence.security.url_validation import UnsafeURLError, validate_url

MAX_BROWSER_REQUESTS = 200
MAX_BROWSER_TEXT_CHARS = 100_000
MAX_BROWSER_LINKS = 100
MAX_SCREENSHOT_BYTES = 2_000_000


class BrowserPolicyError(ValueError):
    """Browser request or resource violates acquisition policy."""


def validate_browser_resource_url(value: str) -> str:
    """Normalize HTTP(S) URLs and reject obvious local or non-routable IP literals.

    DNS resolution and connection-time IP pinning are enforced by the egress proxy;
    this function is an early application-layer filter, not the sole SSRF control.
    """
    try:
        normalized = validate_url(value).normalized
        parsed = urlsplit(normalized)
        host = parsed.hostname
        if not host:
            raise BrowserPolicyError("URL has no hostname")
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            address = None
        if address is not None and not address.is_global:
            raise BrowserPolicyError("non-public IP literals are forbidden")
        if parsed.scheme != "https":
            raise BrowserPolicyError("browser acquisition requires HTTPS")
        if parsed.port not in (None, 443):
            raise BrowserPolicyError("HTTPS is permitted only on port 443")
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path or "/", parsed.query, ""))
    except (UnsafeURLError, ValueError) as exc:
        if isinstance(exc, BrowserPolicyError):
            raise
        raise BrowserPolicyError("URL rejected by browser acquisition policy") from exc


def normalize_browser_payload(payload: dict[str, object]) -> dict[str, Any]:
    allowed = {"url", "wait_until", "timeout_ms", "include_screenshot"}
    if set(payload) - allowed:
        raise BrowserPolicyError("unsupported browser payload field")
    url = payload.get("url")
    if not isinstance(url, str):
        raise BrowserPolicyError("url must be a string")
    wait_until = payload.get("wait_until", "domcontentloaded")
    if not isinstance(wait_until, str) or wait_until not in {"domcontentloaded", "load"}:
        raise BrowserPolicyError("wait_until must be domcontentloaded or load")
    timeout_ms = payload.get("timeout_ms", 15_000)
    if isinstance(timeout_ms, bool) or not isinstance(timeout_ms, int) or not 1_000 <= timeout_ms <= 30_000:
        raise BrowserPolicyError("timeout_ms must be an integer from 1000 to 30000")
    include_screenshot = payload.get("include_screenshot", False)
    if not isinstance(include_screenshot, bool):
        raise BrowserPolicyError("include_screenshot must be a boolean")
    return {
        "url": validate_browser_resource_url(url),
        "wait_until": wait_until,
        "timeout_ms": timeout_ms,
        "include_screenshot": include_screenshot,
    }
