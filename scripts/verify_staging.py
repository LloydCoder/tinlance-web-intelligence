"""Run a low-impact HTTPS readiness and authorization smoke test against staging."""

from __future__ import annotations

import json
import os
import ssl
import uuid
from collections.abc import Callable
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import (
    HTTPRedirectHandler,
    HTTPSHandler,
    Request,
    build_opener,
)

ResponsePair = tuple[int, bytes]
Requester = Callable[[str, str, str | None, bytes | None], ResponsePair]


class VerificationError(ValueError):
    """Raised when staging target configuration is unsafe or incomplete."""


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(
        self,
        req: Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> None:
        return None


def _request(url: str, method: str, token: str | None, body: bytes | None) -> ResponsePair:
    try:
        parsed = urlsplit(url)
    except ValueError as exc:
        raise VerificationError("staging endpoint URL is malformed") from exc
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise VerificationError("staging endpoint requests must use a clean HTTPS URL")
    request = Request(
        url,
        data=body,
        method=method,
        headers={
            "Accept": "application/json",
            "User-Agent": "Tinlance-Web-Intelligence-Staging-Probe/1.0",
            **({"Authorization": f"Bearer {token}"} if token else {}),
            **({"Content-Type": "application/json"} if body is not None else {}),
        },
    )
    opener = build_opener(
        HTTPSHandler(context=ssl.create_default_context()),
        _NoRedirectHandler(),
    )
    try:
        with opener.open(request, timeout=8) as response:  # nosec B310 - HTTPS is validated above
            return response.status, response.read(65_537)
    except HTTPError as exc:
        return exc.code, exc.read(65_537)
    except (URLError, TimeoutError, ssl.SSLError, OSError) as exc:
        raise VerificationError("staging endpoint request failed") from exc


def _json_status(status: int, body: bytes, expected: str) -> bool:
    if status != 200 or len(body) > 65_536:
        return False
    try:
        value = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return False
    return isinstance(value, dict) and value.get("status") == expected


def verify_staging(
    base_url: str,
    token: str | None = None,
    *,
    requester: Requester | None = None,
) -> dict[str, Any]:
    try:
        parsed = urlsplit(base_url)
        hostname = parsed.hostname
    except ValueError as exc:
        raise VerificationError("TWI_STAGING_BASE_URL is malformed") from exc
    if (
        parsed.scheme != "https"
        or not hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise VerificationError(
            "TWI_STAGING_BASE_URL must be HTTPS and omit credentials, query, and fragment"
        )
    if token is not None and (not token or token != token.strip()):
        raise VerificationError("staging probe token must be non-empty and normalized")
    base = base_url.rstrip("/")
    send = requester or _request
    checks: dict[str, dict[str, Any]] = {}

    status, body = send(f"{base}/health/live", "GET", None, None)
    checks["liveness"] = {
        "ok": _json_status(status, body, "ok"),
        "status_code": status,
    }

    status, body = send(f"{base}/health/ready", "GET", None, None)
    checks["readiness"] = {
        "ok": _json_status(status, body, "ready"),
        "status_code": status,
    }

    status, _ = send(f"{base}/v1/jobs", "POST", None, b"{}")
    checks["unauthenticated_write_denied"] = {
        "ok": status == 401,
        "status_code": status,
    }

    status, _ = send(f"{base}/docs", "GET", None, None)
    checks["interactive_docs_disabled"] = {
        "ok": status == 404,
        "status_code": status,
    }

    if token is not None:
        probe_id = str(uuid.uuid4())
        status, _ = send(f"{base}/v1/jobs/{probe_id}", "GET", token, None)
        checks["platform_token_authenticated"] = {
            "ok": status in {403, 404},
            "status_code": status,
        }

    return {"ok": all(check["ok"] for check in checks.values()), "checks": checks}


def main() -> int:
    base_url = os.environ.get("TWI_STAGING_BASE_URL", "")
    token = os.environ.get("TWI_STAGING_PROBE_TOKEN") or None
    try:
        result = verify_staging(base_url, token)
    except VerificationError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
