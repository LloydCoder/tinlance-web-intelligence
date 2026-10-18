"""Leased worker for idempotent source-evidence delivery to World Intelligence."""

from __future__ import annotations

import time

from tinlance_web_intelligence.integrations.world_intelligence.client import (
    WorldIntelligenceDeliveryError,
    WorldIntelligenceEvidenceClient,
)
from tinlance_web_intelligence.integrations.world_intelligence.outbox import (
    SQLiteSourceEvidenceOutbox,
)


class WorldIntelligenceExportWorker:
    def __init__(
        self,
        outbox: SQLiteSourceEvidenceOutbox,
        client: WorldIntelligenceEvidenceClient,
        *,
        worker_id: str,
    ) -> None:
        if not worker_id or len(worker_id) > 128:
            raise ValueError("worker_id must be 1 to 128 characters")
        self._outbox = outbox
        self._client = client
        self._worker_id = worker_id

    def run_once(self) -> bool:
        event = self._outbox.claim_next(self._worker_id, lease_seconds=60)
        if event is None:
            return False
        if event.lease_token is None:
            raise RuntimeError("claimed outbox event has no lease token")
        try:
            remote_id = self._client.send(event)
        except WorldIntelligenceDeliveryError as exc:
            self._outbox.fail(
                event.event_id,
                event.lease_token,
                error_code=exc.error_code,
                retryable=exc.retryable,
            )
            return True
        self._outbox.complete(event.event_id, event.lease_token, remote_id)
        return True

    def run_forever(self, *, poll_interval_seconds: float = 0.5) -> None:
        if not 0.1 <= poll_interval_seconds <= 10:
            raise ValueError("poll interval must be between 0.1 and 10 seconds")
        while True:
            if not self.run_once():
                time.sleep(poll_interval_seconds)
