"""Authenticated client for the trusted browser-job broker."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from tinlance_web_intelligence.browser.policies import BrowserPolicyError, normalize_browser_payload
from tinlance_web_intelligence.browser.service import BrowserCaptureError, BrowserService
from tinlance_web_intelligence.config import ConfigurationError, Settings
from tinlance_web_intelligence.observability.tracing import (
    extract_valid_traceparent,
    inject_current_traceparent,
    start_span,
)

logger = logging.getLogger(__name__)


def _trace_headers() -> dict[str, str]:
    headers: dict[str, str] = {}
    inject_current_traceparent(headers)
    return headers


class BrowserBrokerWorker:
    def __init__(self, settings: Settings, service: BrowserService) -> None:
        if not settings.browser_broker_url or not settings.browser_broker_token:
            raise ConfigurationError("browser worker requires authenticated broker configuration")
        self._service = service
        self._client = httpx.AsyncClient(
            base_url=settings.browser_broker_url,
            headers={"Authorization": f"Bearer {settings.browser_broker_token}"},
            timeout=httpx.Timeout(10.0, connect=3.0),
            trust_env=False,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def run_forever(self) -> None:
        while True:
            try:
                response = await self._client.post(
                    "/internal/browser-jobs/claim", json={}, headers=_trace_headers()
                )
                if response.status_code == 204:
                    await asyncio.sleep(0.5)
                    continue
                if response.status_code in {401, 403}:
                    raise ConfigurationError("browser broker authentication failed")
                response.raise_for_status()
                claim = response.json()
                if not isinstance(claim, dict) or set(claim) != {
                    "job_id", "payload", "lease_token", "attempts", "traceparent"
                }:
                    raise RuntimeError("browser broker returned an invalid claim")
                job_id = claim["job_id"]
                lease_token = claim["lease_token"]
                payload = claim["payload"]
                if (
                    not isinstance(job_id, str)
                    or not 1 <= len(job_id) <= 64
                    or not isinstance(lease_token, str)
                    or len(lease_token) < 32
                    or not isinstance(payload, dict)
                ):
                    raise RuntimeError("browser broker returned invalid claim fields")
                parent = None
                traceparent = extract_valid_traceparent(
                    {"traceparent": claim["traceparent"]}
                    if isinstance(claim["traceparent"], str)
                    else {}
                )
                if traceparent:
                    from opentelemetry.propagate import extract

                    parent = extract({"traceparent": traceparent})
                with start_span(
                    "twi.browser.execute",
                    {"operation": "capture", "component": "browser"},
                    parent=parent,
                ):
                    await self._execute_claim(job_id, lease_token, payload)
            except ConfigurationError:
                raise
            except (httpx.HTTPError, ValueError, RuntimeError) as exc:
                logger.warning("browser broker cycle failed (%s)", type(exc).__name__)
                await asyncio.sleep(1)

    async def _execute_claim(
        self, job_id: str, lease_token: str, payload: dict[str, Any]
    ) -> None:
        try:
            normalized = normalize_browser_payload(payload)
            result = await self._service.capture(
                url=normalized["url"],
                wait_until=normalized["wait_until"],
                timeout_ms=normalized["timeout_ms"],
                include_screenshot=normalized["include_screenshot"],
            )
        except BrowserCaptureError as exc:
            await self._report_failure(job_id, lease_token, exc.error_code, exc.retryable)
            return
        except BrowserPolicyError:
            await self._report_failure(job_id, lease_token, "browser_policy_rejected", False)
            return
        except Exception as exc:
            logger.warning("browser job failed (%s)", type(exc).__name__)
            await self._report_failure(job_id, lease_token, "browser_worker_error", False)
            return

        try:
            response = await self._client.post(
                f"/internal/browser-jobs/{job_id}/complete",
                json={"lease_token": lease_token, "result": result},
                headers=_trace_headers(),
            )
            if response.status_code == 409:
                logger.warning("browser job lease expired before result commit")
                return
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("browser result delivery failed (%s)", type(exc).__name__)

    async def _report_failure(
        self, job_id: str, lease_token: str, error_code: str, retryable: bool
    ) -> None:
        try:
            response = await self._client.post(
                f"/internal/browser-jobs/{job_id}/fail",
                json={
                    "lease_token": lease_token,
                    "error_code": error_code,
                    "retryable": retryable,
                },
                headers=_trace_headers(),
            )
            if response.status_code == 409:
                logger.warning("browser job lease expired before failure commit")
                return
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("browser failure delivery failed (%s)", type(exc).__name__)
