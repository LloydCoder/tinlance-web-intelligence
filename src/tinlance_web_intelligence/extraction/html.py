"""Small deterministic HTML extractor with bounded output and no script execution."""

from __future__ import annotations

from html.parser import HTMLParser
from urllib.parse import urljoin

from tinlance_web_intelligence.acquisition.models import ExtractedPage
from tinlance_web_intelligence.security.url_validation import UnsafeURLError, validate_url


class _PageParser(HTMLParser):
    _SKIP = {"script", "style", "noscript", "svg", "template"}

    def __init__(self, base_url: str, max_text_chars: int) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.max_text_chars = max_text_chars
        self.title_parts: list[str] = []
        self.description: str | None = None
        self.canonical_url: str | None = None
        self.text_parts: list[str] = []
        self.links: list[str] = []
        self._in_title = False
        self._skip_depth = 0
        self._link_count = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag in self._SKIP:
            self._skip_depth += 1
        if tag == "title":
            self._in_title = True
        if tag == "meta":
            name = (values.get("name") or values.get("property") or "").lower()
            if name in {"description", "og:description", "twitter:description"}:
                candidate = (values.get("content") or "").strip()
                if candidate and self.description is None:
                    self.description = candidate[:1000]
        if tag == "link" and "canonical" in (values.get("rel") or "").lower():
            href = values.get("href")
            if href:
                self.canonical_url = self._safe_link(href)
        if tag == "a" and values.get("href") and self._link_count < 500:
            href = self._safe_link(values["href"] or "")
            if href and href not in self.links:
                self.links.append(href)
                self._link_count += 1
        if tag in {"p", "div", "br", "li", "h1", "h2", "h3", "section", "article"}:
            self.text_parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag in self._SKIP and self._skip_depth:
            self._skip_depth -= 1
        if tag == "title":
            self._in_title = False
        if tag in {"p", "div", "br", "li", "h1", "h2", "h3", "section", "article"}:
            self.text_parts.append(" ")

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        value = data.strip()
        if not value:
            return
        if self._in_title:
            self.title_parts.append(value)
        self.text_parts.append(value[: self.max_text_chars])

    def _safe_link(self, href: str) -> str | None:
        absolute = urljoin(self.base_url, href.strip())
        try:
            return validate_url(absolute).normalized
        except (UnsafeURLError, ValueError):
            return None


def extract_html(html: str, base_url: str, *, max_text_chars: int = 200_000) -> ExtractedPage:
    if max_text_chars < 1:
        raise ValueError("max_text_chars must be positive")
    base = validate_url(base_url).normalized
    parser = _PageParser(base, max_text_chars)
    parser.feed(html[:5_000_000])
    parser.close()
    title = " ".join(parser.title_parts).strip() or None
    text = " ".join(" ".join(parser.text_parts).split())[:max_text_chars]
    canonical = parser.canonical_url
    if canonical is not None:
        try:
            canonical = validate_url(canonical).normalized
        except UnsafeURLError:
            canonical = None
    return ExtractedPage(title, parser.description, canonical, text, tuple(parser.links))
