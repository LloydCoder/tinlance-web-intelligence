from __future__ import annotations

import unittest
import uuid
from unittest.mock import Mock

from tinlance_web_intelligence.integrations.world_intelligence.client import (
    WorldIntelligenceDeliveryError,
    WorldIntelligenceEvidenceClient,
)
from tinlance_web_intelligence.integrations.world_intelligence.outbox import (
    SQLiteSourceEvidenceOutbox,
)
from tinlance_web_intelligence.integrations.world_intelligence.worker import (
    WorldIntelligenceExportWorker,
)


class WorldIntelligenceExportWorkerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.outbox = SQLiteSourceEvidenceOutbox(":memory:")
        self.outbox.enqueue(
            tenant_ref="a" * 64,
            subject_ref="b" * 64,
            idempotency_key="worker-test-idempotency-0001",
            payload={"schema_version": "1.0.0"},
            request_id="worker-test-request",
            traceparent=None,
        )

    def tearDown(self) -> None:
        self.outbox.close()

    def test_successful_delivery_acknowledges_outbox_event(self) -> None:
        remote_id = str(uuid.uuid4())
        client = Mock(spec=WorldIntelligenceEvidenceClient)
        client.send.return_value = remote_id
        worker = WorldIntelligenceExportWorker(self.outbox, client, worker_id="test-worker")

        self.assertTrue(worker.run_once())
        # The event is delivered and therefore no longer available for another claim.
        self.assertIsNone(self.outbox.claim_next("read-worker"))
        client.send.assert_called_once()
        claimed = client.send.call_args.args[0]
        stored = self.outbox.get(claimed.event_id, "a" * 64, "b" * 64)
        self.assertIsNotNone(stored)
        assert stored is not None
        self.assertEqual(stored.status, "delivered")
        self.assertEqual(stored.remote_evidence_id, remote_id)

    def test_retryable_delivery_error_returns_event_to_pending(self) -> None:
        client = Mock(spec=WorldIntelligenceEvidenceClient)
        client.send.side_effect = WorldIntelligenceDeliveryError(
            "remote_timeout", retryable=True
        )
        worker = WorldIntelligenceExportWorker(self.outbox, client, worker_id="test-worker")
        self.assertTrue(worker.run_once())
        # The retry is delayed by backoff; the stored record remains pending.
        claimed_event = client.send.call_args.args[0]
        stored = self.outbox.get(claimed_event.event_id, "a" * 64, "b" * 64)
        self.assertIsNotNone(stored)
        assert stored is not None
        self.assertEqual(stored.status, "pending")
        self.assertEqual(stored.attempts, 1)


if __name__ == "__main__":
    unittest.main()
