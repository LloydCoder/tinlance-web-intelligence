from __future__ import annotations

import unittest
import uuid

import httpx

from tinlance_web_intelligence.integrations.world_intelligence.client import (
    WorldIntelligenceDeliveryError,
    WorldIntelligenceEvidenceClient,
    redact_source_url,
)
from tinlance_web_intelligence.integrations.world_intelligence.outbox import (
    SQLiteSourceEvidenceOutbox,
)


class WorldIntelligenceClientTests(unittest.TestCase):
    def _claimed_event(self):
        outbox = SQLiteSourceEvidenceOutbox(":memory:")
        event, _ = outbox.enqueue(
            tenant_ref="a" * 64,
            subject_ref="b" * 64,
            idempotency_key="client-test-idempotency-0001",
            payload={"schema_version": "1.0.0", "source_system": "tinlance-web-intelligence"},
            request_id="client-test-request",
            traceparent="00-0123456789abcdef0123456789abcdef-0123456789abcdef-01",
        )
        claimed = outbox.claim_next("client-test-worker")
        self.assertIsNotNone(claimed)
        assert claimed is not None
        return outbox, claimed

    def test_success_posts_to_fixed_endpoint_with_idempotency_and_trace_context(self) -> None:
        evidence_id = str(uuid.uuid4())
        seen: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            return httpx.Response(201, json={"evidence_id": evidence_id, "status": "candidate"})

        outbox, event = self._claimed_event()
        client = WorldIntelligenceEvidenceClient(
            "https://world-intelligence.example",
            "x" * 40,
            transport=httpx.MockTransport(handler),
        )
        try:
            result = client.send(event)
            self.assertEqual(result, evidence_id)
            self.assertEqual(len(seen), 1)
            self.assertEqual(str(seen[0].url), "https://world-intelligence.example/v1/source-evidence")
            self.assertEqual(seen[0].headers["authorization"], "Bearer " + "x" * 40)
            self.assertEqual(seen[0].headers["idempotency-key"], event.idempotency_key)
            self.assertEqual(seen[0].headers["traceparent"], event.traceparent)
        finally:
            client.close()
            outbox.close()

    def test_redirects_are_not_followed_and_are_terminal(self) -> None:
        seen: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            return httpx.Response(302, headers={"Location": "https://attacker.example/"})

        outbox, event = self._claimed_event()
        client = WorldIntelligenceEvidenceClient(
            "https://world-intelligence.example",
            "x" * 40,
            transport=httpx.MockTransport(handler),
        )
        try:
            with self.assertRaises(WorldIntelligenceDeliveryError) as caught:
                client.send(event)
            self.assertEqual(caught.exception.error_code, "remote_rejected_source_evidence")
            self.assertFalse(caught.exception.retryable)
            self.assertEqual(len(seen), 1)
        finally:
            client.close()
            outbox.close()

    def test_server_errors_are_retryable_and_url_validation_is_strict(self) -> None:
        outbox, event = self._claimed_event()
        client = WorldIntelligenceEvidenceClient(
            "https://world-intelligence.example",
            "x" * 40,
            transport=httpx.MockTransport(lambda _request: httpx.Response(503)),
        )
        try:
            with self.assertRaises(WorldIntelligenceDeliveryError) as caught:
                client.send(event)
            self.assertTrue(caught.exception.retryable)
        finally:
            client.close()
            outbox.close()
        with self.assertRaises(ValueError):
            WorldIntelligenceEvidenceClient("http://world-intelligence.example", "x" * 40)
        with self.assertRaises(ValueError):
            WorldIntelligenceEvidenceClient(
                "https://user:pass@world-intelligence.example", "x" * 40
            )

    def test_source_url_redacts_sensitive_query_values(self) -> None:
        result = redact_source_url(
            "https://example.com/path?topic=product&access_token=super-secret&api_key=key-value#section"
        )
        self.assertIn("topic=product", result)
        self.assertNotIn("super-secret", result)
        self.assertNotIn("key-value", result)
        self.assertNotIn("#section", result)
        self.assertIn("REDACTED", result)


if __name__ == "__main__":
    unittest.main()
