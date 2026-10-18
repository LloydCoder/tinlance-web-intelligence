"""Run the dedicated authenticated public-web egress proxy."""

from __future__ import annotations

import asyncio
import logging

from tinlance_web_intelligence.security.egress_proxy import SafeEgressProxy, config_from_env


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    proxy = SafeEgressProxy(config_from_env())
    try:
        asyncio.run(proxy.serve_forever())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
