"""Run the trusted internal browser-job broker service."""

from __future__ import annotations

import os

import uvicorn

from tinlance_web_intelligence.browser.broker_api import create_app
from tinlance_web_intelligence.config import Settings
from tinlance_web_intelligence.persistence.factory import create_job_repository


def main() -> None:
    settings = Settings.from_env(require_identity=False)
    service_token = os.environ.get("TWI_BROWSER_BROKER_TOKEN", "")
    repository = create_job_repository(settings)
    app = create_app(repository, service_token)
    # This service is reachable only on the private broker networks in Compose.
    uvicorn.run(
        app,
        host="0.0.0.0",  # noqa: S104  # nosec B104 - container network isolation is the access boundary
        port=8081,
        access_log=False,
    )


if __name__ == "__main__":
    main()
