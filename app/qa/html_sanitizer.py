"""Strips dangerous HTML from DeepSeek's translated output before it's
used anywhere downstream (WordPress payloads, Elementor fields).

The Translator prompt asks DeepSeek to preserve inline formatting tags
exactly (<strong>, <em>, <a href="...">, etc. -- prompt_builder.py rule
15) and translate only the visible text. That's a request, not a
guarantee: nothing stops a hallucinated response from including a
<script> tag or an `onclick`/`javascript:` payload, and nothing in the
write path downstream would otherwise catch it -- WordPress renders
post content as real HTML once a translation is published, same as it
would for a human editor's raw HTML. This is the one place that closes
that gap, allowlist-based rather than trying to blocklist every
dangerous pattern.
"""
from __future__ import annotations

from bs4 import BeautifulSoup
from bs4.element import Tag

_ALLOWED_TAGS = {"strong", "b", "em", "i", "u", "span", "br", "a"}
_ALLOWED_ATTRS = {"a": {"href", "title"}}
_ALLOWED_URL_SCHEMES = {"http", "https", "mailto", "tel"}

# Tags whose *content* is code/style, not visible prose -- dropped entirely
# (not unwrapped) so their contents never end up as stray visible text.
_STRIP_ENTIRELY_TAGS = {"script", "style", "iframe", "object", "embed", "noscript"}


def _is_safe_href(value: str) -> bool:
    value = value.strip()
    if value.startswith("/") or value.startswith("#"):
        return True  # relative/anchor links carry no scheme to check
    if ":" not in value:
        return True  # relative path with no leading slash, e.g. "docs/page"
    scheme = value.split(":", 1)[0].strip().lower()
    return scheme in _ALLOWED_URL_SCHEMES


def sanitize_html(html_fragment: str) -> str:
    """Removes any tag not in the allowlist (keeping its inner text),
    strips every attribute except the few explicitly allowed per tag, and
    rejects `javascript:`/`data:`-style href schemes. `on*` event
    attributes are dropped along with everything else not explicitly
    allowed -- there's no allowlist entry for them on any tag.
    """
    if "<" not in html_fragment:
        return html_fragment  # fast path: plain text, nothing to parse

    soup = BeautifulSoup(html_fragment, "html.parser")

    for tag in soup.find_all(True):
        if not isinstance(tag, Tag) or getattr(tag, "decomposed", False):
            continue  # already removed as a descendant of an earlier decompose() call
        if tag.name in _STRIP_ENTIRELY_TAGS:
            tag.decompose()
            continue
        if tag.name not in _ALLOWED_TAGS:
            tag.unwrap()
            continue

        allowed_attrs = _ALLOWED_ATTRS.get(tag.name, set())
        for attr in list(tag.attrs):
            if attr not in allowed_attrs:
                del tag[attr]

        if tag.name == "a" and "href" in tag.attrs and not _is_safe_href(tag["href"]):
            del tag["href"]

    return str(soup)
