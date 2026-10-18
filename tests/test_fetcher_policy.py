import asyncio

import pytest

from tinlance_web_intelligence.acquisition.fetcher import (
    FetchError,
    SafeHTTPFetcher,
    headers_for_redirect,
)
from tinlance_web_intelligence.security.url_validation import validate_url


def test_redirect_preserves_credentials_only_within_same_origin() -> None:
    source = validate_url("https://api.example.com/search")
    same_origin = validate_url("https://api.example.com/next")
    other_origin = validate_url("https://attacker.example/collect")
    headers = {
        "User-Agent": "TWI-test",
        "X-Subscription-Token": "never-forward-cross-origin",
        "Authorization": "Bearer secret",
        "Accept": "application/json",
    }
    assert headers_for_redirect(headers, source, same_origin) == headers
    redirected = headers_for_redirect(headers, source, other_origin)
    assert redirected == {"User-Agent": "TWI-test", "Accept": "application/json"}


def test_redirect_strips_credentials_on_scheme_or_port_change() -> None:
    source = validate_url("https://api.example.com/search")
    downgrade = validate_url("http://api.example.com/search")
    headers = {"Authorization": "Bearer secret", "X-API-Key": "secret"}
    assert headers_for_redirect(headers, source, downgrade) == {}


def test_transport_managed_headers_cannot_be_overridden() -> None:
    with pytest.raises(FetchError):
        asyncio.run(
            SafeHTTPFetcher().fetch(
                "https://example.com", headers={"Host": "attacker.example"}
            )
        )
