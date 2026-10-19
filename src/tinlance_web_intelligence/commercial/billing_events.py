"""Provider-neutral signed billing event verification and usage reconciliation primitives.

No payment provider is selected here. Provider adapters must verify raw request bytes
before parsing, persist event receipts idempotently, and keep payment/invoice authority
outside TWI. The verifier deliberately returns a payload digest, not customer payload data.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import time
from dataclasses import dataclass
from datetime import datetime


class BillingEventError(ValueError):
    """A signed billing event failed validation."""


@dataclass(frozen=True, slots=True)
class VerifiedBillingEvent:
    event_id: str
    event_type: str
    occurred_at: str
    received_timestamp: int
    payload_sha256: str
    schema_version: int = 1


@dataclass(frozen=True, slots=True)
class UsageFact:
    event_id: str
    quantity: int


@dataclass(frozen=True, slots=True)
class BillingFact:
    event_id: str
    quantity: int
    status: str


@dataclass(frozen=True, slots=True)
class ReconciliationFinding:
    event_id: str
    classification: str
    usage_quantity: int | None
    billing_quantity: int | None
    billing_status: str | None


_EVENT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,199}$")
_EVENT_TYPE = re.compile(r"^[a-z][a-z0-9_.-]{0,99}$")
_SIGNATURE = re.compile(r"^sha256=([0-9a-f]{64})$")


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise BillingEventError("billing event JSON contains duplicate keys")
        result[key] = value
    return result


def verify_signed_billing_event(
    raw_body: bytes,
    *,
    timestamp_header: str,
    signature_header: str,
    secret: bytes,
    now_epoch: int | None = None,
    tolerance_seconds: int = 300,
) -> VerifiedBillingEvent:
    """Verify HMAC-SHA256 over timestamp + '.' + raw body before trusting fields."""
    if not isinstance(raw_body, bytes) or not raw_body or len(raw_body) > 1_048_576:
        raise BillingEventError("billing event body must contain 1 to 1048576 bytes")
    if not isinstance(secret, bytes) or len(secret) < 32:
        raise BillingEventError("billing webhook secret must contain at least 32 bytes")
    if (
        not timestamp_header.isascii()
        or not timestamp_header.isdecimal()
        or len(timestamp_header) > 12
    ):
        raise BillingEventError("billing event timestamp is invalid")
    if not 30 <= tolerance_seconds <= 900:
        raise BillingEventError("signature tolerance must be between 30 and 900 seconds")
    timestamp = int(timestamp_header)
    now = int(time.time()) if now_epoch is None else now_epoch
    if timestamp > now + tolerance_seconds or now - timestamp > tolerance_seconds:
        raise BillingEventError("billing event signature timestamp is outside the accepted window")
    match = _SIGNATURE.fullmatch(signature_header)
    if match is None:
        raise BillingEventError("billing event signature format is invalid")
    signed_payload = timestamp_header.encode("ascii") + b"." + raw_body
    expected = hmac.new(secret, signed_payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, match.group(1)):
        raise BillingEventError("billing event signature verification failed")
    try:
        envelope = json.loads(raw_body, object_pairs_hook=_reject_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BillingEventError("billing event body is not valid JSON") from exc
    if not isinstance(envelope, dict):
        raise BillingEventError("billing event envelope must be an object")
    if set(envelope) != {"event_id", "event_type", "occurred_at", "data"}:
        raise BillingEventError("billing event envelope fields are invalid")
    event_id = envelope["event_id"]
    event_type = envelope["event_type"]
    occurred_at = envelope["occurred_at"]
    data = envelope["data"]
    if not isinstance(event_id, str) or not _EVENT_ID.fullmatch(event_id):
        raise BillingEventError("billing event ID is invalid")
    if not isinstance(event_type, str) or not _EVENT_TYPE.fullmatch(event_type):
        raise BillingEventError("billing event type is invalid")
    if not isinstance(occurred_at, str) or len(occurred_at) > 40:
        raise BillingEventError("billing event occurrence timestamp is invalid")
    try:
        parsed = datetime.fromisoformat(occurred_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise BillingEventError("billing event occurrence timestamp is invalid") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise BillingEventError("billing event occurrence timestamp must include a timezone")
    if not isinstance(data, dict):
        raise BillingEventError("billing event data must be an object")
    return VerifiedBillingEvent(
        event_id=event_id,
        event_type=event_type,
        occurred_at=parsed.isoformat(),
        received_timestamp=timestamp,
        payload_sha256=hashlib.sha256(raw_body).hexdigest(),
    )


def reconcile_usage(
    usage_facts: list[UsageFact], billing_facts: list[BillingFact]
) -> list[ReconciliationFinding]:
    """Return deterministic findings without mutating either source ledger."""
    usage_by_id: dict[str, list[UsageFact]] = {}
    billing_by_id: dict[str, list[BillingFact]] = {}
    for usage_fact in usage_facts:
        if (
            not usage_fact.event_id
            or isinstance(usage_fact.quantity, bool)
            or not isinstance(usage_fact.quantity, int)
            or usage_fact.quantity < 1
        ):
            raise ValueError("usage facts require an event ID and positive integer quantity")
        usage_by_id.setdefault(usage_fact.event_id, []).append(usage_fact)
    for billing_fact in billing_facts:
        if (
            not billing_fact.event_id
            or isinstance(billing_fact.quantity, bool)
            or not isinstance(billing_fact.quantity, int)
            or billing_fact.quantity < 1
            or not billing_fact.status
            or len(billing_fact.status) > 40
        ):
            raise ValueError("billing facts require an event ID, positive quantity, and status")
        billing_by_id.setdefault(billing_fact.event_id, []).append(billing_fact)
    findings: list[ReconciliationFinding] = []
    for event_id in sorted(set(usage_by_id) | set(billing_by_id)):
        usage_rows = usage_by_id.get(event_id, [])
        billing_rows = billing_by_id.get(event_id, [])
        usage_quantity = sum(usage_fact.quantity for usage_fact in usage_rows) if usage_rows else None
        billing_quantity = (
            sum(billing_fact.quantity for billing_fact in billing_rows) if billing_rows else None
        )
        status = ",".join(sorted(billing_fact.status for billing_fact in billing_rows)) or None
        if len(usage_rows) > 1 or len(billing_rows) > 1:
            classification = "duplicate_records"
        elif not billing_rows:
            classification = "usage_missing_in_billing"
        elif not usage_rows:
            classification = "billing_missing_in_usage"
        elif any(
            billing_fact.status.lower() in {"refunded", "reversed", "voided", "unknown"}
            for billing_fact in billing_rows
        ):
            classification = "manual_review"
        elif usage_quantity != billing_quantity:
            classification = "quantity_mismatch"
        else:
            classification = "matched"
        findings.append(
            ReconciliationFinding(
                event_id=event_id,
                classification=classification,
                usage_quantity=usage_quantity,
                billing_quantity=billing_quantity,
                billing_status=status,
            )
        )
    return findings



def decide_event_order(
    *, current_revision: int | None, incoming_revision: int | None
) -> str:
    """Order events only with a provider-guaranteed monotonic resource revision.

    Timestamps alone are not treated as a total order. If the provider cannot supply
    comparable revisions, the adapter must refresh authoritative state or request review.
    """
    for revision in (current_revision, incoming_revision):
        if revision is not None and (
            isinstance(revision, bool) or not isinstance(revision, int) or revision < 0
        ):
            raise ValueError("provider resource revisions must be non-negative integers")
    if current_revision is None or incoming_revision is None:
        return "manual_review"
    if incoming_revision > current_revision:
        return "apply"
    if incoming_revision < current_revision:
        return "stale"
    return "manual_review"
