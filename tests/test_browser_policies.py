from __future__ import annotations

import pytest

from tinlance_web_intelligence.browser.policies import (
    BrowserPolicyError,
    normalize_browser_payload,
    validate_browser_resource_url,
)


@pytest.mark.parametrize("url", [
    "http://127.0.0.1/",
    "http://169.254.169.254/latest/meta-data/",
    "http://10.0.0.1/",
    "https://[::1]/",
    "file:///etc/passwd",
    "ftp://example.com/",
    "https://example.com:8443/",
])
def test_browser_rejects_local_non_http_and_nonstandard_destinations(url: str) -> None:
    with pytest.raises(BrowserPolicyError):
        validate_browser_resource_url(url)


def test_browser_url_normalization_and_payload_bounds() -> None:
    assert validate_browser_resource_url("https://example.com/path#fragment") == "https://example.com/path"
    assert normalize_browser_payload({"url": "https://example.com"}) == {
        "url": "https://example.com/",
        "wait_until": "domcontentloaded",
        "timeout_ms": 15000,
        "include_screenshot": False,
    }
    with pytest.raises(BrowserPolicyError):
        normalize_browser_payload({"url": "https://example.com", "timeout_ms": True})
    with pytest.raises(BrowserPolicyError):
        normalize_browser_payload({"url": "https://example.com", "click": "button"})
