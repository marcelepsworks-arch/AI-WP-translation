from app.qa.html_sanitizer import sanitize_html


def test_sanitize_html_leaves_plain_text_untouched():
    assert sanitize_html("Just plain text.") == "Just plain text."


def test_sanitize_html_preserves_allowed_inline_tags():
    html = 'Read the <strong>manual</strong> and <a href="https://example.com/docs">docs</a>.'
    assert sanitize_html(html) == html


def test_sanitize_html_strips_script_tag_and_its_content():
    result = sanitize_html("Hello <script>alert('x')</script> world.")
    assert "<script" not in result
    assert "alert" not in result
    assert "Hello" in result and "world." in result


def test_sanitize_html_strips_style_and_iframe_content():
    result = sanitize_html("<style>body{color:red}</style><iframe src='evil.com'></iframe>Text")
    assert "<style" not in result
    assert "<iframe" not in result
    assert "color:red" not in result
    assert "Text" in result


def test_sanitize_html_unwraps_disallowed_tag_but_keeps_text():
    result = sanitize_html("<div onclick=\"steal()\">Important paragraph</div>")
    assert "<div" not in result
    assert "onclick" not in result
    assert "Important paragraph" in result


def test_sanitize_html_strips_on_attributes_from_allowed_tags():
    result = sanitize_html('<a href="https://example.com" onclick="steal()">link</a>')
    assert "onclick" not in result
    assert 'href="https://example.com"' in result


def test_sanitize_html_rejects_javascript_scheme_href():
    result = sanitize_html("<a href=\"javascript:alert(1)\">click me</a>")
    assert "javascript:" not in result
    assert "href" not in result
    assert "click me" in result


def test_sanitize_html_rejects_data_scheme_href():
    result = sanitize_html('<a href="data:text/html,evil">click</a>')
    assert "data:" not in result


def test_sanitize_html_allows_relative_and_anchor_hrefs():
    result = sanitize_html('<a href="/docs/page">link</a> <a href="#section">anchor</a>')
    assert 'href="/docs/page"' in result
    assert 'href="#section"' in result


def test_sanitize_html_drops_attributes_not_in_allowlist_for_span():
    result = sanitize_html('<span style="color:red" class="x">styled text</span>')
    assert result == "<span>styled text</span>"
