"""Tenant-scoped customer usage reads; billing state remains owned externally."""
from __future__ import annotations

import base64
import binascii
import json
import re
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from tinlance_web_intelligence.auth.principal import Principal
from tinlance_web_intelligence.commercial.usage_ledger import UsageEvent

router = APIRouter(prefix="/v1/usage", tags=["usage"])
_CURSOR_EVENT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,199}$")


def _decode_cursor(cursor: str | None) -> tuple[str, str] | None:
    if cursor is None:
        return None
    if not cursor or len(cursor) > 1024:
        raise HTTPException(status_code=422, detail="usage cursor is invalid")
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        payload = base64.urlsafe_b64decode(padded.encode("ascii"))
        value = json.loads(payload)
    except (ValueError, UnicodeDecodeError, binascii.Error) as exc:
        raise HTTPException(status_code=422, detail="usage cursor is invalid") from exc
    if not isinstance(value, dict) or set(value) != {"occurred_at", "event_id"}:
        raise HTTPException(status_code=422, detail="usage cursor is invalid")
    occurred_at = value["occurred_at"]
    event_id = value["event_id"]
    if (
        not isinstance(occurred_at, str)
        or len(occurred_at) > 40
        or not isinstance(event_id, str)
        or not _CURSOR_EVENT_ID.fullmatch(event_id)
    ):
        raise HTTPException(status_code=422, detail="usage cursor is invalid")
    try:
        parsed = datetime.fromisoformat(occurred_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="usage cursor is invalid") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise HTTPException(status_code=422, detail="usage cursor is invalid")
    return parsed.isoformat(), event_id


def _encode_cursor(event: UsageEvent) -> str:
    payload = json.dumps(
        {"occurred_at": event.occurred_at, "event_id": event.event_id},
        sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    return base64.urlsafe_b64encode(payload).rstrip(b"=").decode("ascii")


def _principal(request: Request) -> Principal:
    principal = getattr(request.state, "principal", None)
    if not isinstance(principal, Principal):
        raise HTTPException(status_code=401, detail="authentication required")
    return principal


def _public_event(event: UsageEvent) -> dict[str, Any]:
    return {
        "event_id": event.event_id,
        "feature": event.feature,
        "dimension": event.dimension,
        "period_start": event.period_start,
        "quantity": event.quantity,
        "occurred_at": event.occurred_at,
        "schema_version": event.schema_version,
    }


@router.get("")
def read_usage(
    request: Request,
    dimension: str = Query(..., min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_.:-]+$"),
    period_start: str = Query(..., min_length=1, max_length=40),
    limit: int = Query(100, ge=1, le=500),
    cursor: str | None = Query(None, max_length=1024),
) -> dict[str, Any]:
    """Return usage facts for the verified subject, never caller-supplied identity."""
    principal = _principal(request)
    if "twi:usage:read" not in principal.scopes and "twi:usage:read:any" not in principal.scopes:
        raise HTTPException(status_code=403, detail="required scope is missing")
    try:
        parsed = datetime.fromisoformat(period_start.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(
            status_code=422, detail="period_start must be an ISO-8601 timestamp"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise HTTPException(status_code=422, detail="period_start must include a timezone")
    canonical_period_start = parsed.astimezone(UTC).isoformat().replace("+00:00", "Z")
    ledger = request.app.state.usage_ledger
    read_any = "twi:usage:read:any" in principal.scopes
    usage_subject_id = None if read_any else principal.subject_id
    after = _decode_cursor(cursor)
    fetched = ledger.list_events(
        tenant_id=principal.tenant_id, subject_id=usage_subject_id, limit=limit + 1,
        dimension=dimension, period_start=canonical_period_start, after=after,
    )
    has_more = len(fetched) > limit
    scoped = fetched[:limit]
    next_cursor = _encode_cursor(scoped[-1]) if has_more and scoped else None
    total = ledger.usage_total(
        tenant_id=principal.tenant_id, subject_id=usage_subject_id,
        dimension=dimension, period_start=canonical_period_start,
    )
    quota_limit: int | None = None
    plan_id: str | None = None
    plan_version: int | None = None
    resolver = request.app.state.entitlement_resolver
    if resolver is not None:
        try:
            plan = resolver.resolve(
                tenant_id=principal.tenant_id, subject_id=principal.subject_id
            )
        except Exception as exc:
            raise HTTPException(
                status_code=503, detail="commercial entitlement state unavailable"
            ) from exc
        if plan is None:
            raise HTTPException(status_code=503, detail="commercial entitlement state unavailable")
        quota_limit = plan.limits.get(dimension)
        if quota_limit is None:
            raise HTTPException(status_code=503, detail="quota dimension is not configured")
        plan_id = plan.plan_id
        plan_version = plan.version
    return {
        "schema_version": 1,
        "dimension": dimension,
        "period_start": canonical_period_start,
        "used": total,
        "quota_limit": quota_limit,
        "remaining": max(0, quota_limit - total) if quota_limit is not None else None,
        "plan_id": plan_id,
        "plan_version": plan_version,
        "events": [_public_event(event) for event in scoped],
        "returned": len(scoped),
        "has_more": has_more,
        "next_cursor": next_cursor,
    }
