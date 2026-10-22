from __future__ import annotations

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from playwright.sync_api import Browser, sync_playwright

WEB_ROOT = Path(__file__).resolve().parents[1] / "apps" / "web"
DIST_ROOT = WEB_ROOT / "dist"


class QuietStaticHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> None:
    if not (DIST_ROOT / "index.html").is_file():
        raise SystemExit("Frontend dist is missing; run npm run build before browser tests.")

    server = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        partial(QuietStaticHandler, directory=str(DIST_ROOT)),
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}/"

    try:
        with sync_playwright() as playwright:
            browser: Browser = playwright.chromium.launch(headless=True, args=["--no-sandbox"])
            try:
                page = browser.new_page(viewport={"width": 1440, "height": 1000})
                page_errors: list[str] = []
                failed_local_requests: list[str] = []
                page.on("pageerror", lambda error: page_errors.append(str(error)))
                page.on(
                    "requestfailed",
                    lambda request: failed_local_requests.append(request.url)
                    if request.url.startswith(base_url)
                    else None,
                )
                response = page.goto(base_url, wait_until="networkidle")
                assert response is not None and response.status == 200, (
                    "Tinlyt document did not load"
                )
                assert page.title() == "Tinlyt — Web Intelligence"
                assert page.locator("main#main").count() == 1
                assert page.locator("h1").count() == 1
                assert "Illustrative example" in page.locator(".panel-note").inner_text()
                assert page.get_by_role("link", name="Request early access").count() >= 1

                # The public navigation becomes a keyboard-operable disclosure at mobile width.
                page.set_viewport_size({"width": 375, "height": 812})
                page.reload(wait_until="networkidle")
                menu_button = page.locator(".site-nav-toggle")
                assert menu_button.is_visible()
                menu_button.click()
                assert menu_button.get_attribute("aria-expanded") == "true"
                assert page.get_by_role("navigation", name="Main navigation").is_visible()
                page.keyboard.press("Escape")
                assert menu_button.get_attribute("aria-expanded") == "false"
                assert page.evaluate(
                    "document.activeElement?.classList.contains('site-nav-toggle')"
                )

                # The landing route and workspace have separate contracts. Run the existing
                # interactive-workspace accessibility suite against the preserved app document.
                response = page.goto(base_url + "app.html", wait_until="networkidle")
                assert response is not None and response.status == 200, (
                    "Tinlyt workspace document did not load"
                )
                assert page.title() == "Tinlyt — Web Intelligence"
                assert page.locator("aside.sidebar").count() == 1

                # Semantic landmarks, navigation destinations, unique IDs and accessible names.
                audit = page.evaluate(
                    """() => {
                      const ids = [...document.querySelectorAll('[id]')].map(node => node.id);
                      const duplicates = ids.filter((id, index) => ids.indexOf(id) !== index);
                      const nav = [...document.querySelectorAll('a.nav-link')].map(link => ({
                        href: link.getAttribute('href'),
                        label: (link.getAttribute('aria-label') || link.textContent || '').trim(),
                        targetExists: link.getAttribute('href')?.startsWith('#')
                          ? Boolean(document.getElementById(link.getAttribute('href').slice(1)))
                          : true
                      }));
                      const controls = [...document.querySelectorAll(
                        'input:not([type="hidden"]), select, textarea'
                      )].map(el => ({
                        id: el.id,
                        labelled: Boolean(
                          el.getAttribute('aria-label')
                          || el.getAttribute('aria-labelledby')
                          || [...document.querySelectorAll('label')].some(
                            label => label.htmlFor === el.id
                          )
                          || el.closest('label')
                        )
                      }));
                      const buttons = [...document.querySelectorAll('button')].filter(el => {
                        const style = getComputedStyle(el);
                        return style.display !== 'none'
                          && style.visibility !== 'hidden'
                          && el.getClientRects().length > 0;
                      }).map(el => ({
                        label: (
                          el.getAttribute('aria-label')
                          || el.getAttribute('title')
                          || el.innerText
                          || ''
                        ).trim(),
                        disabled: el.disabled
                      }));
                      return { duplicates, nav, controls, buttons };
                    }"""
                )
                assert not audit["duplicates"], f"Duplicate IDs: {audit['duplicates']}"
                assert all(
                    item["label"] and item["targetExists"] for item in audit["nav"]
                ), audit["nav"]
                assert all(item["labelled"] for item in audit["controls"]), audit["controls"]
                assert all(item["label"] for item in audit["buttons"]), audit["buttons"]

                # The first keyboard stop is the skip link and Enter moves focus to main.
                page.keyboard.press("Tab")
                assert page.evaluate(
                    "document.activeElement?.classList.contains('skip-link')"
                ), "Skip link is not first in keyboard order"
                page.keyboard.press("Enter")
                assert page.evaluate(
                    "document.activeElement?.id === 'main'"
                ), "Skip link did not move focus to main"

                # Keyboard focus must remain visible, including in system forced-colors mode.
                page.emulate_media(forced_colors="active")
                page.keyboard.press("Tab")
                focus_style = page.evaluate(
                    """() => {
                      const el = document.activeElement;
                      const style = getComputedStyle(el);
                      return {
                        tag: el?.tagName,
                        outlineStyle: style.outlineStyle,
                        outlineWidth: style.outlineWidth
                      };
                    }"""
                )
                assert focus_style["outlineStyle"] == "solid", focus_style
                assert float(focus_style["outlineWidth"].removesuffix("px")) >= 2, focus_style
                page.emulate_media(forced_colors="none")

                # Check representative text roles against their actual composited backgrounds.
                contrast_samples = page.evaluate(
                    """() => {
                      const selectors = [
                        'body', '.nav-link', '.nav-link.is-active',
                        '#runtime-message', '#mode-description',
                        '.field-help', '#usage-status'
                      ];
                      const rgb = value => value.match(/[0-9.]+/g)?.map(Number) || [];
                      const luminance = value => {
                        const values = rgb(value).slice(0, 3).map(v => {
                          const c = v / 255;
                          return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
                        });
                        return values[0] * 0.2126 + values[1] * 0.7152 + values[2] * 0.0722;
                      };
                      const effectiveBackground = element => {
                        let current = element;
                        while (current) {
                          const color = getComputedStyle(current).backgroundColor;
                          const values = rgb(color);
                          if (values.length < 4 || values[3] > 0.99) return color;
                          current = current.parentElement;
                        }
                        return 'rgb(255, 255, 255)';
                      };
                      return selectors.map(selector => {
                        const element = document.querySelector(selector);
                        if (!element) return { selector, missing: true };
                        const foreground = getComputedStyle(element).color;
                        const background = effectiveBackground(element);
                        const values = [luminance(foreground), luminance(background)]
                          .sort((a, b) => b - a);
                        return {
                          selector,
                          ratio: (values[0] + 0.05) / (values[1] + 0.05),
                          foreground,
                          background
                        };
                      });
                    }"""
                )
                assert all(
                    not sample.get("missing") for sample in contrast_samples
                ), contrast_samples
                assert all(sample["ratio"] >= 4.5 for sample in contrast_samples), contrast_samples

                # Mobile layout must reflow without document-level horizontal scrolling.
                page.set_viewport_size({"width": 375, "height": 812})
                page.reload(wait_until="networkidle")
                overflow = page.evaluate(
                    """() => {
                      const offenders = [...document.querySelectorAll('body *')].map(el => {
                        const rect = el.getBoundingClientRect();
                        const style = getComputedStyle(el);
                        return {
                          tag: el.tagName,
                          id: el.id,
                          className: typeof el.className === 'string' ? el.className : '',
                          left: Math.round(rect.left),
                          right: Math.round(rect.right),
                          width: Math.round(rect.width),
                          overflowX: style.overflowX,
                          parentOverflowX: getComputedStyle(
                            el.parentElement || document.body
                          ).overflowX
                        };
                      }).filter(el => el.width > 0 && el.right > window.innerWidth + 1
                        && !['auto', 'scroll', 'hidden', 'clip'].includes(el.parentOverflowX))
                        .sort((a, b) => b.right - a.right).slice(0, 8);
                      return {
                        document: document.documentElement.scrollWidth,
                        viewport: window.innerWidth,
                        offenders
                      };
                    }"""
                )
                assert overflow["document"] <= overflow["viewport"], overflow

                # Workspace navigation opens as a drawer, and choosing a destination closes it.
                drawer_button = page.locator(".workspace-nav-toggle")
                assert drawer_button.is_visible()
                drawer_button.click()
                assert drawer_button.get_attribute("aria-expanded") == "true"
                page.locator('a.nav-link[href="#usage"]').click()
                assert drawer_button.get_attribute("aria-expanded") == "false"
                assert page.url.endswith("#usage")
                assert page.locator("#usage").is_visible()

                # Reduced-motion preference disables smooth scrolling and long transitions.
                page.emulate_media(reduced_motion="reduce")
                motion = page.evaluate(
                    """() => ({
                      scrollBehavior: getComputedStyle(document.documentElement).scrollBehavior,
                      transitionDuration: getComputedStyle(
                        document.querySelector('.nav-link')
                      ).transitionDuration
                    })"""
                )
                assert motion["scrollBehavior"] == "auto", motion
                duration = motion["transitionDuration"].split(",")[0].strip()
                seconds = (
                    float(duration.removesuffix("ms")) / 1000
                    if duration.endswith("ms")
                    else float(duration.removesuffix("s"))
                )
                assert seconds <= 0.001, motion

                assert not page_errors, f"Uncaught browser errors: {page_errors}"
                assert not failed_local_requests, f"Failed local resources: {failed_local_requests}"
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


if __name__ == "__main__":
    main()
