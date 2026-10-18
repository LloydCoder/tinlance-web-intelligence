"""Playwright-based read-only capture; all browser traffic uses the isolated proxy."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import os
from collections.abc import Mapping
from contextlib import suppress
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from tinlance_web_intelligence.browser.policies import (
    MAX_BROWSER_LINKS,
    MAX_BROWSER_REQUESTS,
    MAX_BROWSER_TEXT_CHARS,
    MAX_SCREENSHOT_BYTES,
    BrowserPolicyError,
    normalize_browser_payload,
    validate_browser_resource_url,
)
from tinlance_web_intelligence.config import ConfigurationError, Settings


class BrowserCaptureError(RuntimeError):
    """Sanitized browser execution failure safe to store in job metadata."""

    def __init__(self, error_code: str, *, retryable: bool = False) -> None:
        super().__init__(error_code)
        self.error_code = error_code
        self.retryable = retryable


class BrowserService:
    def __init__(self, settings: Settings) -> None:
        if not settings.browser_enabled:
            raise ConfigurationError("browser acquisition is disabled")
        proxy_url = settings.browser_proxy_url
        proxy_username = settings.browser_proxy_username
        proxy_password = settings.browser_proxy_password
        if proxy_url is None or proxy_username is None or proxy_password is None:
            raise ConfigurationError("browser service requires an authenticated egress proxy")
        self._proxy: Any = {
            "server": proxy_url,
            "username": proxy_username,
            "password": proxy_password,
        }

    @staticmethod
    def _browser_environment(source: Mapping[str, str] | None = None) -> dict[str, str]:
        """Pass only non-secret runtime variables to the untrusted browser process."""
        values = os.environ if source is None else source
        allowed = {
            "PATH",
            "PLAYWRIGHT_BROWSERS_PATH",
            "LANG",
            "LC_ALL",
            "TZ",
            "FONTCONFIG_PATH",
        }
        environment = {key: values[key] for key in allowed if key in values}
        temporary_directory = os.path.join(os.sep, "tmp")
        environment["HOME"] = temporary_directory
        environment["TMPDIR"] = temporary_directory
        return environment

    async def capture(
        self,
        *,
        url: str,
        wait_until: str = "domcontentloaded",
        timeout_ms: int = 15_000,
        include_screenshot: bool = False,
    ) -> dict[str, Any]:
        try:
            request = normalize_browser_payload({
                "url": url,
                "wait_until": wait_until,
                "timeout_ms": timeout_ms,
                "include_screenshot": include_screenshot,
            })
        except BrowserPolicyError as exc:
            raise BrowserCaptureError("browser_policy_rejected") from exc

        from playwright.async_api import Error as PlaywrightError
        from playwright.async_api import TimeoutError as PlaywrightTimeoutError
        from playwright.async_api import async_playwright

        request_count = 0
        policy_rejections = 0
        browser: Any = None
        context: Any = None
        try:
            async with asyncio.timeout(request["timeout_ms"] / 1000 + 10):
                async with async_playwright() as playwright:
                    browser = await playwright.chromium.launch(
                        headless=True,
                        chromium_sandbox=True,
                        proxy=self._proxy,
                        env=self._browser_environment(),
                        args=[
                            "--disable-background-networking",
                            "--disable-extensions",
                            "--disable-sync",
                        ],
                    )
                    context = await browser.new_context(
                        accept_downloads=False,
                        service_workers="block",
                        permissions=[],
                        viewport={"width": 1280, "height": 720},
                    )

                    async def route_request(route: Any, browser_request: Any) -> None:
                        nonlocal request_count, policy_rejections
                        request_count += 1
                        if (
                            request_count > MAX_BROWSER_REQUESTS
                            or browser_request.method not in {"GET", "HEAD"}
                        ):
                            policy_rejections += 1
                            await route.abort("blockedbyclient")
                            return
                        try:
                            validate_browser_resource_url(browser_request.url)
                        except BrowserPolicyError:
                            policy_rejections += 1
                            await route.abort("blockedbyclient")
                            return
                        headers = dict(browser_request.headers)
                        headers.pop("authorization", None)
                        headers.pop("proxy-authorization", None)
                        await route.continue_(headers=headers)

                    await context.route("**/*", route_request)
                    async def block_websocket(websocket: Any) -> None:
                        await websocket.close(
                            code=1008, reason="WebSocket access is disabled"
                        )

                    await context.route_web_socket("**/*", block_websocket)
                    page = await context.new_page()
                    page.on("popup", lambda popup: asyncio.create_task(popup.close()))
                    response = await page.goto(
                        request["url"],
                        wait_until=request["wait_until"],
                        timeout=request["timeout_ms"],
                    )
                    final_url = self._normalize_final_url(page.url)
                    extracted = await page.evaluate(
                        """() => ({
                          text: (document.body?.innerText || '').slice(0, 100000),
                          links: Array.from(document.querySelectorAll('a[href]'))
                            .slice(0, 100)
                            .map(a => ({
                              text: (a.innerText || a.getAttribute('aria-label') || '')
                                .trim().slice(0, 300),
                              url: a.href
                            }))
                        })"""
                    )
                    text = extracted.get("text", "") if isinstance(extracted, dict) else ""
                    if not isinstance(text, str):
                        text = ""
                    links: list[dict[str, str]] = []
                    raw_links = extracted.get("links", []) if isinstance(extracted, dict) else []
                    if isinstance(raw_links, list):
                        for item in raw_links[:MAX_BROWSER_LINKS]:
                            if not isinstance(item, dict) or not isinstance(item.get("url"), str):
                                continue
                            try:
                                link_url = validate_browser_resource_url(item["url"])
                            except BrowserPolicyError:
                                continue
                            link_text = item.get("text", "")
                            links.append(
                                {
                                    "url": link_url,
                                    "text": link_text[:300]
                                    if isinstance(link_text, str)
                                    else "",
                                }
                            )
                    result: dict[str, Any] = {
                        "provider": "playwright-chromium",
                        "source_url": final_url,
                        "retrieved_at": datetime.now(UTC).isoformat(),
                        "status_code": response.status if response is not None else None,
                        "title": (await page.title())[:500],
                        "text": text[:MAX_BROWSER_TEXT_CHARS],
                        "links": links,
                        "content_sha256": hashlib.sha256(
                            text[:MAX_BROWSER_TEXT_CHARS].encode()
                        ).hexdigest(),
                        "request_count": request_count,
                        "policy_rejections": policy_rejections,
                    }
                    if request["include_screenshot"]:
                        try:
                            screenshot = await page.screenshot(
                                type="jpeg", quality=60, full_page=False, timeout=5_000
                            )
                        except PlaywrightError:
                            screenshot = b""
                        if screenshot and len(screenshot) <= MAX_SCREENSHOT_BYTES:
                            result["screenshot_media_type"] = "image/jpeg"
                            result["screenshot_sha256"] = hashlib.sha256(screenshot).hexdigest()
                            result["screenshot_base64"] = base64.b64encode(
                                screenshot
                            ).decode("ascii")
                        else:
                            result["screenshot_omitted_reason"] = "size_limit_or_capture_failure"
                    return result
        except PlaywrightTimeoutError as exc:
            raise BrowserCaptureError("browser_timeout", retryable=True) from exc
        except TimeoutError as exc:
            raise BrowserCaptureError("browser_timeout", retryable=True) from exc
        except PlaywrightError as exc:
            raise BrowserCaptureError("browser_navigation_failed", retryable=True) from exc
        finally:
            if context is not None:
                with suppress(Exception):
                    await context.close()
            if browser is not None:
                with suppress(Exception):
                    await browser.close()

    @staticmethod
    def _normalize_final_url(url: str) -> str:
        parsed = urlsplit(url)
        without_fragment = urlunsplit(
            (parsed.scheme, parsed.netloc, parsed.path, parsed.query, "")
        )
        try:
            return validate_browser_resource_url(without_fragment)
        except BrowserPolicyError as exc:
            raise BrowserCaptureError("browser_policy_rejected") from exc
