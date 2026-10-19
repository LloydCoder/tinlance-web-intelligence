"""Tenant-scoped customer usage reads; billing state remains owned externally."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from tinlance_web_intelligence.auth.principal import Principal
from tinlance_web_intelligence.commercial.usage_ledger import UsageEvent

router = APIRouter(prefix="/v1/usage", tags=["usage"])


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
) -> dict[str, Any]:
    """Return usage facts for the verified subject, never caller-supplied identity."""
    principal = _principal(request)
    if "twi:usage:read" not in principal.scopes and "twi:usage:read:any" not in principal.scopes:
        raise HTTPException(status_code=403, detail="required scope is missing")
    try:
        parsed = datetime.fromisoformat(period_start.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="period_start must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise HTTPException(status_code=422, detail="period_start must include a timezone")
    ledger = request.app.state.usage_ledger
    events = ledger.list_events(
        tenant_id=principal.tenant_id, subject_id=principal.subject_id, limit=limit
    )
    scoped = [
        event for event in events
        if event.dimension == dimension and event.period_start == period_start
    ]
    total = ledger.usage_total(
        tenant_id=principal.tenant_id, subject_id=principal.subject_id,
        dimension=dimension, period_start=period_start,
    )
    return {
        "schema_version": 1,
        "dimension": dimension,
        "period_start": period_start,
        "used": total,
        "events": [_public_event(event) for event in scoped],
        "returned": len(scoped),
    }
