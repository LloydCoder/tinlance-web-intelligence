"""Consume browser-only jobs in a dedicated worker process."""

from __future__ import annotations

import os
import time

from tinlance_web_intelligence.browser.service import BrowserService
from tinlance_web_intelligence.config import Settings
from tinlance_web_intelligence.jobs.repository import SQLiteJobRepository
from tinlance_web_intelligence.jobs.worker import JobWorker


def main() -> None:
    settings = Settings.from_env(require_identity=False)
    if not settings.browser_enabled:
        raise RuntimeError("browser worker refuses to start unless TWI_BROWSER_ENABLED=true")
    repository = SQLiteJobRepository(settings.database_path)
    worker = JobWorker(
        repository,
        worker_id=os.environ.get("TWI_WORKER_ID", "browser-worker"),
        browser_service=BrowserService(settings),
        allowed_kinds=("browser",),
        lease_seconds=90,
    )
    try:
        while True:
            if not worker.run_once():
                time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        repository.close()


if __name__ == "__main__":
    main()
