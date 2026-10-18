from tinlance_web_intelligence.extraction.html import extract_html


def test_extracts_title_description_text_and_safe_links() -> None:
    html = """<html><head><title>Example News</title>
    <meta name="description" content="A concise summary">
    <link rel="canonical" href="https://example.com/story"></head>
    <body><h1>Headline</h1><p>Useful text <b>with detail</b>.</p>
    <script>window.secret = 'do not include';</script>
    <a href="/about">About</a><a href="javascript:alert(1)">bad</a>
    <a href="http://127.0.0.1/admin">internal</a></body></html>"""
    page = extract_html(html, "https://example.com/index")
    assert page.title == "Example News"
    assert page.description == "A concise summary"
    assert page.canonical_url == "https://example.com/story"
    assert "Headline" in page.text and "Useful text" in page.text
    assert "window.secret" not in page.text
    assert page.links == ("https://example.com/about",)


def test_text_output_is_bounded() -> None:
    page = extract_html("<p>" + ("x" * 1000) + "</p>", "https://example.com", max_text_chars=80)
    assert len(page.text) <= 80
