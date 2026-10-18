"""Bounded HTTP retrieval with manual redirects and connection-time SSRF checks."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from urllib.parse import urljoin

import aiohttp

from tinlance_web_intelligence.acquisition.models import FetchResult
from tinlance_web_intelligence.config import Settings
from tinlance_web_intelligence.security.resolver import PublicOnlyResolver
from tinlance_web_intelligence.security.url_validation import (
    UnsafeURLError,
    ValidatedURL,
    validate_url,
)


class FetchError(RuntimeError):
    """A request was rejected or could not be completed safely."""

    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


_SAFE_CROSS_ORIGIN_HEADERS = frozenset(
    {"user-agent", "accept", "accept-encoding", "accept-language"}
)
_MANAGED_REQUEST_HEADERS = frozenset(
    {"host", "content-length", "transfer-encoding", "connection", "proxy-authorization"}
)


def headers_for_redirect(
    headers: Mapping[str, str], previous: ValidatedURL, target: ValidatedURL
) -> dict[str, str]:
    """Strip all non-safe headers when a redirect crosses an origin boundary."""
    previous_port = previous.port or (443 if previous.scheme == "https" else 80)
    target_port = target.port or (443 if target.scheme == "https" else 80)
    previous_origin = (previous.scheme, previous.hostname, previous_port)
    target_origin = (target.scheme, target.hostname, target_port)
    if previous_origin == target_origin:
        return dict(headers)
    return {
        key: value
        for key, value in headers.items()
        if key.lower() in _SAFE_CROSS_ORIGIN_HEADERS
    }


class SafeHTTPFetcher:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings.from_env()

    async def fetch(
        self, url: str, *, headers: Mapping[str, str] | None = None
    ) -> FetchResult:
        requested = validate_url(url, allowed_schemes=self.settings.allowed_schemes)
        timeout = aiohttp.ClientTimeout(
            total=self.settings.request_timeout_seconds,
            connect=min(5.0, self.settings.request_timeout_seconds),
            sock_read=self.settings.request_timeout_seconds,
        )
        request_headers = {
            "User-Agent": self.settings.user_agent,
            "Accept": "text/html, text/plain, application/json;q=0.9, */*;q=0.1",
            "Accept-Encoding": "identity",
        }
        if headers:
            for key, value in headers.items():
                if key.lower() in _MANAGED_REQUEST_HEADERS:
                    raise FetchError("request attempted to override a transport-managed header")
                request_headers[key] = value
        request_headers["Accept-Encoding"] = "identity"
        connector = aiohttp.TCPConnector(
            resolver=PublicOnlyResolver(),
            use_dns_cache=False,
            limit=20,
            limit_per_host=4,
            force_close=True,
        )
        current = requested
        try:
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                trust_env=False,
                auto_decompress=False,
                cookie_jar=aiohttp.DummyCookieJar(),
            ) as session:
                for redirect_count in range(self.settings.max_redirects + 1):
                    async with session.get(
                        current.normalized,
                        headers=request_headers,
                        allow_redirects=False,
                    ) as response:
                        if response.status in {301, 302, 303, 307, 308}:
                            if redirect_count >= self.settings.max_redirects:
                                raise FetchError("redirect limit exceeded")
                            location = response.headers.get("Location")
                            if not location:
                                raise FetchError("redirect response lacks a Location header")
                            try:
                                target = validate_url(
                                    urljoin(current.normalized, location),
                                    allowed_schemes=self.settings.allowed_schemes,
                                )
                            except UnsafeURLError as exc:
                                raise FetchError("redirect destination rejected by policy") from exc
                            request_headers = headers_for_redirect(request_headers, current, target)
                            current = target
                            continue
                        if not 200 <= response.status < 300:
                            retryable = response.status in {408, 425, 429} or response.status >= 500
                            raise FetchError(
                                f"upstream returned HTTP {response.status}", retryable=retryable
                            )
                        encoding = response.headers.get("Content-Encoding", "identity").lower()
                        if encoding not in {"", "identity"}:
                            raise FetchError(
                                "compressed responses are not accepted by this fetcher"
                            )
                        declared = response.headers.get("Content-Length")
                        if declared is not None:
                            try:
                                if int(declared) > self.settings.max_response_bytes:
                                    raise FetchError("response exceeds configured byte limit")
                            except ValueError as exc:
                                raise FetchError("invalid Content-Length header") from exc
                        body = bytearray()
                        async for chunk in response.content.iter_chunked(65536):
                            if len(body) + len(chunk) > self.settings.max_response_bytes:
                                raise FetchError("response exceeds configured byte limit")
                            body.extend(chunk)
                        safe_headers = {
                            key.lower(): response.headers[key]
                            for key in ("Content-Type", "ETag", "Last-Modified")
                            if key in response.headers
                        }
                        content_type = response.headers.get(
                            "Content-Type", "application/octet-stream"
                        )
                        return FetchResult(
                            requested_url=requested.normalized,
                            final_url=current.normalized,
                            status_code=response.status,
                            content_type=content_type.split(";", maxsplit=1)[0].strip().lower(),
                            body=bytes(body),
                            retrieved_at=datetime.now(UTC),
                            headers=safe_headers,
                        )
        except (aiohttp.ClientError, TimeoutError) as exc:
            raise FetchError("upstream request failed", retryable=True) from exc
        raise FetchError("request did not produce a response")
