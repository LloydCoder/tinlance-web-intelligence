from __future__ import annotations

import hashlib
import unittest
from unittest.mock import patch

from tinlance_web_intelligence.integrations.world_intelligence.outbox import (
    OutboxConflictError,
    OutboxLeaseLostError,
    SQLiteSourceEvidenceOutbox,
)


def _ref(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


class SourceEvidenceOutboxTests(unittest.TestCase):
    def setUp(self) -> None:
        self.outbox = SQLiteSourceEvidenceOutbox(":memory:")
        self.tenant_ref = _ref("tenant-a")
        self.subject_ref = _ref("subject-a")
        self.payload = {
            "schema_version": "1.0.0",
            "source_system": "tinlance-web-intelligence",
            "statement": "A candidate source-backed statement.",
        }

    def tearDown(self) -> None:
        self.outbox.close()

    def enqueue(self, *, key: str = "source-evidence-idempotency-0001", payload=None):
        return self.outbox.enqueue(
            tenant_ref=self.tenant_ref,
            subject_ref=self.subject_ref,
            idempotency_key=key,
            payload=self.payload if payload is None else payload,
            request_id="outbox-test",
            traceparent=None,
        )

    def test_enqueue_is_idempotent_and_rejects_payload_conflict(self) -> None:
        first, replayed = self.enqueue()
        second, replay = self.enqueue()
        self.assertFalse(replayed)
        self.assertTrue(replay)
        self.assertEqual(first.event_id, second.event_id)

        with self.assertRaises(OutboxConflictError):
            self.enqueue(payload={**self.payload, "statement": "Changed statement."})

    def test_expired_lease_gets_a_new_token_and_stale_worker_cannot_complete(self) -> None:
        with patch("tinlance_web_intelligence.integrations.world_intelligence.outbox.time.time", return_value=100):
            self.enqueue()
            first = self.outbox.claim_next("same-worker", lease_seconds=5)
        self.assertIsNotNone(first)
        assert first is not None and first.lease_token is not None

        with patch("tinlance_web_intelligence.integrations.world_intelligence.outbox.time.time", return_value=106):
            second = self.outbox.claim_next("same-worker", lease_seconds=5)
        self.assertIsNotNone(second)
        assert second is not None and second.lease_token is not None
        self.assertNotEqual(first.lease_token, second.lease_token)

        with self.assertRaises(OutboxLeaseLostError):
            self.outbox.complete(first.event_id, first.lease_token, "remote-id")
        completed = self.outbox.complete(second.event_id, second.lease_token, "remote-id")
        self.assertEqual(completed.status, "delivered")
        self.assertEqual(completed.remote_evidence_id, "remote-id")

    def test_retryable_failure_uses_backoff_and_terminal_failure_stops_retrying(self) -> None:
        with patch("tinlance_web_intelligence.integrations.world_intelligence.outbox.time.time", return_value=100):
            self.enqueue()
            first = self.outbox.claim_next("worker", lease_seconds=10)
        assert first is not None and first.lease_token is not None
        with patch("tinlance_web_intelligence.integrations.world_intelligence.outbox.time.time", return_value=101):
            retry = self.outbox.fail(
                first.event_id,
                first.lease_token,
                error_code="remote_unavailable",
                retryable=True,
            )
        self.assertEqual(retry.status, "pending")

        with patch("tinlance_web_intelligence.integrations.world_intelligence.outbox.time.time", return_value=102):
            self.assertIsNone(self.outbox.claim_next("worker", lease_seconds=10))
        with patch("tinlance_web_intelligence.integrations.world_intelligence.outbox.time.time", return_value=104):
            second = self.outbox.claim_next("worker", lease_seconds=10)
        assert second is not None and second.lease_token is not None
        with patch("tinlance_web_intelligence.integrations.world_intelligence.outbox.time.time", return_value=105):
            terminal = self.outbox.fail(
                second.event_id,
                second.lease_token,
                error_code="remote_rejected",
                retryable=False,
            )
        self.assertEqual(terminal.status, "failed")

    def test_export_status_is_scoped_to_tenant_and_subject(self) -> None:
        event, _ = self.enqueue()
        self.assertIsNotNone(self.outbox.get(event.event_id, self.tenant_ref, self.subject_ref))
        self.assertIsNone(self.outbox.get(event.event_id, _ref("tenant-b"), self.subject_ref))
        self.assertIsNone(self.outbox.get(event.event_id, self.tenant_ref, _ref("subject-b")))


if __name__ == "__main__":
    unittest.main()
