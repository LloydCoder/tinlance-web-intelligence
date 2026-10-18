from __future__ import annotations

import asyncio
import os

import pytest


@pytest.mark.skipif(
    os.environ.get("TWI_RUN_BROWSER_INTEGRATION") != "1",
    reason="browser sandbox smoke test runs in its dedicated CI step",
)
def test_chromium_launches_and_fresh_contexts_are_isolated() -> None:
    from playwright.async_api import async_playwright

    async def exercise() -> None:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True, chromium_sandbox=True)
            try:
                first = await browser.new_context()
                first_page = await first.new_page()
                await first_page.goto("about:blank")
                await first_page.evaluate("() => { window.__twiIsolationProbe = 'private'; }")
                second = await browser.new_context()
                second_page = await second.new_page()
                await second_page.goto("about:blank")
                probe = await second_page.evaluate(
                    "() => window.__twiIsolationProbe || null"
                )
                assert probe is None
                await first.close()
                await second.close()
            finally:
                await browser.close()

    asyncio.run(exercise())
