from __future__ import annotations

import hashlib
import hmac
import json

import pytest

from tinlance_web_intelligence.commercial.billing_inbox import (
    BillingEventReceiptConflict,
    SQLiteBillingEventInbox,
)
from tinlance_web_intelligence.commercial.billing_events import (
    BillingEventError,
    BillingFact,
    UsageFact,
    reconcile_usage,
    verify_signed_billing_event,
)

_SECRET = b"test-webhook-secret-that-is-at-least-32-bytes"
_TIMESTAMP = "1800000000"


def signed_body(body: bytes, timestamp: str = _TIMESTAMP) -> str:
    digest = hmac.new(_SECRET, timestamp.encode() + b"." + body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def test_signed_event_verifies_raw_bytes_and_returns_no_payload() -> None:
    body = json.dumps({
        "event_id": "evt_123",
        "event_type": "invoice.paid",
        "occurred_at": "2026-10-19T10:00:00Z",
        "data": {"customer_email": "private@example.test", "amount": 1234},
    }, separators=(",", ":")).encode()
    event = verify_signed_billing_event(
        body, timestamp_header=_TIMESTAMP, signature_header=signed_body(body),
        secret=_SECRET, now_epoch=int(_TIMESTAMP),
    )
    assert event.event_id == "evt_123"
    assert event.event_type == "invoice.paid"
    assert event.payload_sha256 == hashlib.sha256(body).hexdigest()
    assert not hasattr(event, "data")
    assert "private@example.test" not in repr(event)


def test_signed_event_rejects_bad_signature_timestamp_and_secret() -> None:
    body = b'{"event_id":"evt_1","event_type":"usage.recorded","occurred_at":"2026-10-19T10:00:00Z","data":{}}'
    with pytest.raises(BillingEventError, match="signature verification"):
        verify_signed_billing_event(
            body, timestamp_header=_TIMESTAMP, signature_header="sha256=" + "0" * 64,
            secret=_SECRET, now_epoch=int(_TIMESTAMP),
        )
    with pytest.raises(BillingEventError, match="outside"):
        verify_signed_billing_event(
            body, timestamp_header=_TIMESTAMP, signature_header=signed_body(body),
            secret=_SECRET, now_epoch=int(_TIMESTAMP) + 301,
        )
    with pytest.raises(BillingEventError, match="at least 32 bytes"):
        verify_signed_billing_event(
            body, timestamp_header=_TIMESTAMP, signature_header=signed_body(body),
            secret=b"short", now_epoch=int(_TIMESTAMP),
        )


def test_signed_event_rejects_duplicate_keys_and_untrusted_envelope_shape() -> None:
    duplicate = b'{"event_id":"first","event_id":"second","event_type":"invoice.paid","occurred_at":"2026-10-19T10:00:00Z","data":{}}'
    with pytest.raises(BillingEventError, match="duplicate keys"):
        verify_signed_billing_event(
            duplicate, timestamp_header=_TIMESTAMP, signature_header=signed_body(duplicate),
            secret=_SECRET, now_epoch=int(_TIMESTAMP),
        )
    wrong_shape = b'{"event_id":"evt_1","event_type":"invoice.paid","occurred_at":"2026-10-19T10:00:00Z","data":{},"extra":true}'
    with pytest.raises(BillingEventError, match="fields are invalid"):
        verify_signed_billing_event(
            wrong_shape, timestamp_header=_TIMESTAMP, signature_header=signed_body(wrong_shape),
            secret=_SECRET, now_epoch=int(_TIMESTAMP),
        )


def test_reconciliation_classifies_all_mismatches_without_mutation() -> None:
    findings = reconcile_usage(
        [
            UsageFact("match", 2),
            UsageFact("no-billing", 1),
            UsageFact("wrong-quantity", 4),
            UsageFact("duplicate-usage", 1),
            UsageFact("duplicate-usage", 1),
            UsageFact("manual", 1),
        ],
        [
            BillingFact("match", 2, "paid"),
            BillingFact("billing-only", 1, "paid"),
            BillingFact("wrong-quantity", 3, "paid"),
            BillingFact("duplicate-billing", 1, "paid"),
            BillingFact("duplicate-billing", 1, "paid"),
            BillingFact("manual", 1, "refunded"),
        ],
    )
    assert {row.event_id: row.classification for row in findings} == {
        "billing-only": "billing_missing_in_usage",
        "duplicate-billing": "duplicate_records",
        "duplicate-usage": "duplicate_records",
        "manual": "manual_review",
        "match": "matched",
        "no-billing": "usage_missing_in_billing",
        "wrong-quantity": "quantity_mismatch",
    }
    assert findings == sorted(findings, key=lambda row: row.event_id)


def test_reconciliation_rejects_invalid_quantities() -> None:
    with pytest.raises(ValueError):
        reconcile_usage([UsageFact("bad", 0)], [])
    with pytest.raises(ValueError):
        reconcile_usage([], [BillingFact("bad", 1, "")])



def test_billing_inbox_is_durable_idempotent_and_payload_free() -> None:
    body = json.dumps({
        "event_id": "evt_inbox_1",
        "event_type": "invoice.paid",
        "occurred_at": "2026-10-19T10:00:00Z",
        "data": {"private": "must-not-be-stored"},
    }, separators=(",", ":")).encode()
    event = verify_signed_billing_event(
        body, timestamp_header=_TIMESTAMP, signature_header=signed_body(body),
        secret=_SECRET, now_epoch=int(_TIMESTAMP),
    )
    inbox = SQLiteBillingEventInbox(":memory:")
    receipt, replayed = inbox.record(provider_key="provider-a", event=event)
    assert not replayed and receipt.status == "received"
    replay, was_replayed = inbox.record(provider_key="provider-a", event=event)
    assert was_replayed and replay == receipt
    assert "must-not-be-stored" not in repr(inbox.get(
        provider_key="provider-a", event_id="evt_inbox_1"
    ))
    failed = inbox.mark_failed(
        provider_key="provider-a", event_id="evt_inbox_1", error_code="temporary_error"
    )
    assert failed.status == "failed" and failed.attempts == 1
    processed = inbox.mark_processed(provider_key="provider-a", event_id="evt_inbox_1")
    assert processed.status == "processed" and processed.attempts == 2
    assert inbox.mark_processed(
        provider_key="provider-a", event_id="evt_inbox_1"
    ) == processed
    with pytest.raises(ValueError, match="state transition"):
        inbox.mark_failed(
            provider_key="provider-a", event_id="evt_inbox_1", error_code="late_failure"
        )
    changed = type(event)(
        event_id=event.event_id, event_type=event.event_type, occurred_at=event.occurred_at,
        received_timestamp=event.received_timestamp, payload_sha256="f" * 64,
    )
    with pytest.raises(BillingEventReceiptConflict):
        inbox.record(provider_key="provider-a", event=changed)
    inbox.close()


def test_billing_inbox_scopes_same_event_id_by_provider() -> None:
    body = b'{"event_id":"evt_shared","event_type":"invoice.paid","occurred_at":"2026-10-19T10:00:00Z","data":{}}'
    event = verify_signed_billing_event(
        body, timestamp_header=_TIMESTAMP, signature_header=signed_body(body),
        secret=_SECRET, now_epoch=int(_TIMESTAMP),
    )
    inbox = SQLiteBillingEventInbox(":memory:")
    first, _ = inbox.record(provider_key="provider-a", event=event)
    second, replayed = inbox.record(provider_key="provider-b", event=event)
    assert not replayed
    assert first.provider_key != second.provider_key
    inbox.close()
