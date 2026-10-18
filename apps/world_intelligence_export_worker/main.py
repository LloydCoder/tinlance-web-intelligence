"""Run the World Intelligence source-evidence export worker."""

from __future__ import annotations

import os

from tinlance_web_intelligence.config import Settings
from tinlance_web_intelligence.integrations.world_intelligence.client import (
    WorldIntelligenceEvidenceClient,
)
from tinlance_web_intelligence.integrations.world_intelligence.outbox import (
    SQLiteSourceEvidenceOutbox,
)
from tinlance_web_intelligence.integrations.world_intelligence.worker import (
    WorldIntelligenceExportWorker,
)


def main() -> None:
    settings = Settings.from_env(require_identity=False)
    if not settings.world_intelligence_url or not settings.world_intelligence_token:
        raise RuntimeError(
            "World Intelligence export worker requires TWI_WORLD_INTELLIGENCE_URL and "
            "TWI_WORLD_INTELLIGENCE_TOKEN"
        )
    outbox = SQLiteSourceEvidenceOutbox(settings.database_path)
    client = WorldIntelligenceEvidenceClient(
        settings.world_intelligence_url,
        settings.world_intelligence_token,
        allow_http_for_development=settings.environment in {"development", "test"},
    )
    worker = WorldIntelligenceExportWorker(
        outbox,
        client,
        worker_id=os.environ.get("TWI_WORKER_ID", "twi-wi-export-worker"),
    )
    try:
        worker.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        client.close()
        outbox.close()


if __name__ == "__main__":
    main()
