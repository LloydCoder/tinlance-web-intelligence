"""Worker entry point: python -m apps.worker.main"""

from __future__ import annotations

import os
import socket
import time

from tinlance_web_intelligence.acquisition.fetcher import SafeHTTPFetcher
from tinlance_web_intelligence.acquisition.service import WebAcquisitionService
from tinlance_web_intelligence.config import Settings
from tinlance_web_intelligence.jobs.worker import JobWorker
from tinlance_web_intelligence.persistence.factory import create_job_repository
from tinlance_web_intelligence.search.brave import BraveSearchProvider


def main() -> None:
    settings = Settings.from_env()
    repository = create_job_repository(settings)
    provider = (
        BraveSearchProvider(settings.brave_api_key, SafeHTTPFetcher(settings))
        if settings.brave_api_key
        else None
    )
    worker = JobWorker(
        repository,
        worker_id=f"{socket.gethostname()}-{os.getpid()}",
        acquisition=WebAcquisitionService(SafeHTTPFetcher(settings)),
        search_provider=provider,
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
