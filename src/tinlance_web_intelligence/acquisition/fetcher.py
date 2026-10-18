"""Bounded HTTP retrieval with manual redirects and connection-time SSRF checks."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Mapping
from urllib.parse import urljoin

import aiohttp

from tinlance_web_intelligence.acquisition.models import FetchResult
from tinlance_web_intelligence.config import Settings
from tinlance_web_intelligence.security.resolver import PublicOnlyResolver
from tinlance_web_intelligence.security.url_validation import UnsafeURLError, validate_url


class FetchError(RuntimeError):
    """A request was rejected or could not be completed safely."""


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
        connector = aiohttp.TCPConnector(
            resolver=PublicOnlyResolver(),
            use_dns_cache=False,
            limit=20,
            limit_per_host=4,
            force_close=True,
        )
        request_headers = {
            "User-Agent": self.settings.user_agent,
            "Accept": "text/html, text/plain, application/json;q=0.9, */*;q=0.1",
            "Accept-Encoding": "identity",
        }
        if headers:
            request_headers.update(headers)
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
                                current = validate_url(
                                    urljoin(current.normalized, location),
                                    allowed_schemes=self.settings.allowed_schemes,
                                )
                            except UnsafeURLError as exc:
                                raise FetchError("redirect destination rejected by policy") from exc
                            continue
                        if not 200 <= response.status < 300:
                            raise FetchError(f"upstream returned HTTP {response.status}")
                        encoding = response.headers.get("Content-Encoding", "identity").lower()
                        if encoding not in {"", "identity"}:
                            raise FetchError("compressed responses are not accepted by this fetcher")
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
                        content_type = response.headers.get("Content-Type", "application/octet-stream")
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
            raise FetchError("upstream request failed") from exc
        raise FetchError("request did not produce a response")
