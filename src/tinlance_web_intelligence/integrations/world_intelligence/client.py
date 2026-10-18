"""Bounded, idempotent client for World Intelligence source-evidence intake."""

from __future__ import annotations

import json
import re
import uuid
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx

from tinlance_web_intelligence.integrations.world_intelligence.outbox import OutboxEvent

_TRACEPARENT = re.compile(r"^[0-9a-f]{2}-[0-9a-f]{32}-[0-9a-f]{16}-[0-9a-f]{2}$")
_SENSITIVE_QUERY_KEYS = {
    "access_token",
    "api_key",
    "apikey",
    "auth",
    "authorization",
    "client_secret",
    "code",
    "credential",
    "key",
    "password",
    "passwd",
    "secret",
    "session",
    "sessionid",
    "signature",
    "sig",
    "token",
}


class WorldIntelligenceDeliveryError(RuntimeError):
    """A bounded delivery failure safe to record in operational state."""

    def __init__(self, error_code: str, *, retryable: bool) -> None:
        super().__init__(error_code)
        self.error_code = error_code
        self.retryable = retryable


def validate_traceparent(value: str | None) -> str | None:
    if value is None:
        return None
    if not _TRACEPARENT.fullmatch(value):
        raise ValueError("invalid traceparent")
    version, trace_id, span_id, _flags = value.split("-")
    if version == "ff" or set(trace_id) == {"0"} or set(span_id) == {"0"}:
        raise ValueError("invalid traceparent identifiers")
    return value


def redact_source_url(value: str) -> str:
    """Remove common secret-bearing query values before exporting source references."""
    parsed = urlsplit(value)
    query: list[tuple[str, str]] = []
    for key, item in parse_qsl(parsed.query, keep_blank_values=True):
        query.append((key, "[REDACTED]" if key.lower() in _SENSITIVE_QUERY_KEYS else item))
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), ""))


class WorldIntelligenceEvidenceClient:
    def __init__(
        self,
        base_url: str,
        service_token: str,
        *,
        timeout_seconds: float = 5.0,
        allow_http_for_development: bool = False,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        parsed = urlsplit(base_url)
        allowed_schemes = {"https", "http"} if allow_http_for_development else {"https"}
        if (
            parsed.scheme not in allowed_schemes
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("World Intelligence URL must be a trusted service origin")
        if len(service_token) < 32 or service_token != service_token.strip():
            raise ValueError("World Intelligence service token must contain at least 32 characters")
        if not 0.1 <= timeout_seconds <= 30:
            raise ValueError("timeout_seconds must be between 0.1 and 30")
        self._base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            timeout=httpx.Timeout(timeout_seconds),
            follow_redirects=False,
            trust_env=False,
            transport=transport,
        )
        self._service_token = service_token

    def send(self, event: OutboxEvent) -> str:
        if event.lease_token is None:
            raise WorldIntelligenceDeliveryError("missing_outbox_lease", retryable=False)
        headers = {
            "Authorization": f"Bearer {self._service_token}",
            "Content-Type": "application/json",
            "Idempotency-Key": event.idempotency_key,
            "X-Request-ID": event.request_id,
        }
        if event.traceparent is not None:
            headers["traceparent"] = event.traceparent
        try:
            with self._client.stream(
                "POST",
                f"{self._base_url}/v1/source-evidence",
                json=event.payload,
                headers=headers,
            ) as response:
                status_code = response.status_code
                if status_code in {429, 500, 502, 503, 504}:
                    raise WorldIntelligenceDeliveryError(
                        "remote_temporarily_unavailable", retryable=True
                    )
                if status_code == 409:
                    raise WorldIntelligenceDeliveryError(
                        "remote_idempotency_conflict", retryable=False
                    )
                if status_code not in {200, 201}:
                    raise WorldIntelligenceDeliveryError(
                        "remote_rejected_source_evidence", retryable=False
                    )
                body = bytearray()
                for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if len(body) > 65_536:
                        raise WorldIntelligenceDeliveryError(
                            "remote_response_too_large", retryable=True
                        )
        except WorldIntelligenceDeliveryError:
            raise
        except httpx.TimeoutException as exc:
            raise WorldIntelligenceDeliveryError("remote_timeout", retryable=True) from exc
        except httpx.TransportError as exc:
            raise WorldIntelligenceDeliveryError("remote_transport_error", retryable=True) from exc

        try:
            payload = json.loads(body)
            evidence_id = payload["evidence_id"]
            if payload.get("status") != "candidate" or not isinstance(evidence_id, str):
                raise ValueError("invalid remote response")
            return str(uuid.UUID(evidence_id))
        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            raise WorldIntelligenceDeliveryError(
                "invalid_remote_response", retryable=True
            ) from exc

    def close(self) -> None:
        self._client.close()
