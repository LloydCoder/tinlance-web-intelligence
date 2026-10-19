from __future__ import annotations

import pytest

from scripts.verify_staging import VerificationError, verify_staging


def test_staging_probe_rejects_non_https_and_url_credentials() -> None:
    with pytest.raises(VerificationError, match="HTTPS"):
        verify_staging("http://staging.example.test")
    with pytest.raises(VerificationError, match="HTTPS"):
        verify_staging("https://user:secret@staging.example.test")


def test_staging_probe_checks_health_auth_and_docs_without_mutation() -> None:
    seen: list[tuple[str, str, str | None, bytes | None]] = []

    def requester(
        url: str, method: str, token: str | None, body: bytes | None
    ) -> tuple[int, bytes]:
        seen.append((url, method, token, body))
        if url.endswith("/health/live"):
            return 200, b'{"status":"ok"}'
        if url.endswith("/health/ready"):
            return 200, b'{"status":"ready"}'
        if url.endswith("/v1/jobs"):
            return 401, b'{"detail":"bearer token required"}'
        if url.endswith("/docs"):
            return 404, b'{"detail":"Not Found"}'
        raise AssertionError("unexpected request")

    result = verify_staging("https://staging.example.test/", requester=requester)
    assert result["ok"] is True
    assert all(check["ok"] for check in result["checks"].values())
    assert len(seen) == 4
    assert seen[2][1:] == ("POST", None, b"{}")


def test_staging_probe_accepts_a_valid_platform_token_without_creating_a_job() -> None:
    def requester(
        url: str, method: str, token: str | None, body: bytes | None
    ) -> tuple[int, bytes]:
        if url.endswith("/health/live"):
            return 200, b'{"status":"ok"}'
        if url.endswith("/health/ready"):
            return 200, b'{"status":"ready"}'
        if url.endswith("/v1/jobs"):
            return 401, b'{}'
        if url.endswith("/docs"):
            return 404, b'{}'
        if "/v1/jobs/" in url:
            assert method == "GET"
            assert token == "platform-probe-token"
            assert body is None
            return 404, b'{"detail":"job not found"}'
        raise AssertionError("unexpected request")

    result = verify_staging(
        "https://staging.example.test", "platform-probe-token", requester=requester
    )
    assert result["ok"] is True
    assert result["checks"]["platform_token_authenticated"]["status_code"] == 404


def test_staging_probe_fails_closed_when_readiness_is_unhealthy() -> None:
    def requester(
        url: str, method: str, token: str | None, body: bytes | None
    ) -> tuple[int, bytes]:
        if url.endswith("/health/live"):
            return 200, b'{"status":"ok"}'
        if url.endswith("/health/ready"):
            return 503, b'{"status":"not_ready"}'
        if url.endswith("/v1/jobs"):
            return 401, b'{}'
        if url.endswith("/docs"):
            return 404, b'{}'
        raise AssertionError("unexpected request")

    result = verify_staging("https://staging.example.test", requester=requester)
    assert result["ok"] is False
    assert result["checks"]["readiness"]["status_code"] == 503
