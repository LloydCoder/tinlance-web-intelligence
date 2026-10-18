import pytest

from tinlance_web_intelligence.security.url_validation import (
    UnsafeURLError,
    is_public_routable_ip,
    validate_url,
)


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "ftp://example.com/a",
        "http://localhost",
        "http://service.local",
        "http://metadata.google.internal",
        "http://127.0.0.1/",
        "http://10.0.0.1/",
        "http://169.254.169.254/latest/meta-data/",
        "http://[::1]/",
        "http://[fd00::1]/",
        "https://user:password@example.com/",
        "https://example.com/#fragment",
        "https://example.com:99999/",
        "http://example.com\\@evil.com/",
        "http://2130706433/",
        " https://example.com",
    ],
)
def test_unsafe_urls_rejected(url: str) -> None:
    with pytest.raises(UnsafeURLError):
        validate_url(url)


@pytest.mark.parametrize(
    "ip",
    [
        "127.0.0.1",
        "10.0.0.1",
        "172.16.0.1",
        "192.168.1.1",
        "169.254.169.254",
        "::1",
        "fe80::1",
        "fc00::1",
        "224.0.0.1",
    ],
)
def test_non_public_ip_rejected(ip: str) -> None:
    assert not is_public_routable_ip(ip)


def test_public_https_url_normalized() -> None:
    result = validate_url("HTTPS://Example.COM/path?q=1")
    assert result.normalized == "https://example.com/path?q=1"
    assert result.hostname == "example.com"


def test_public_literal_ip_allowed_by_syntax_layer() -> None:
    assert validate_url("https://1.1.1.1/").hostname == "1.1.1.1"
