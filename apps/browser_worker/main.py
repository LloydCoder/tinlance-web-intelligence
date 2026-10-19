"""Consume browser-only jobs through the trusted broker, without database access."""

from __future__ import annotations

import asyncio

from tinlance_web_intelligence.browser.broker_client import BrowserBrokerWorker
from tinlance_web_intelligence.browser.service import BrowserService
from tinlance_web_intelligence.config import Settings


async def _serve(worker: BrowserBrokerWorker) -> None:
    try:
        await worker.run_forever()
    finally:
        await worker.close()


def main() -> None:
    settings = Settings.from_env(require_identity=False, require_database=False)
    if not settings.browser_enabled:
        raise RuntimeError("browser worker refuses to start unless TWI_BROWSER_ENABLED=true")
    worker = BrowserBrokerWorker(settings, BrowserService(settings))
    try:
        asyncio.run(_serve(worker))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
