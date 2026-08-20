"""Checks that URLs are never altered by translation — brief section 12.4."""
from __future__ import annotations

import re

from bs4 import BeautifulSoup
from pydantic import BaseModel

_URL_PATTERN = re.compile(r"https?://\S+")
_URL_ATTRS = ("href", "src")


def extract_urls(text: str) -> list[str]:
    """Blocks reach QA as raw inner HTML, not plain text (see
    `app.extraction.html_parser`), so URLs mostly live inside `href`
    attributes. Matching the bare pattern against that markup would run
    `\\S+` straight through the closing quote and into the link text --
    `<a href="https://x.com/k">Basic Starter Kits</a>` yields
    `https://x.com/k">Basic`, whose last word changes the moment the link
    text is translated. Every link whose text is more than one word would
    then be reported as an altered URL. Attributes are read structurally
    instead, and only genuine text nodes are scanned for bare URLs.
    """
    if "<" not in text:
        return _URL_PATTERN.findall(text)

    soup = BeautifulSoup(text, "html.parser")
    urls = [
        value.strip()
        for tag in soup.find_all(True)
        for attr in _URL_ATTRS
        if (value := tag.get(attr)) and isinstance(value, str) and _URL_PATTERN.match(value.strip())
    ]
    return urls + _URL_PATTERN.findall(soup.get_text(" "))


class UrlCheckResult(BaseModel):
    passed: bool
    missing_urls: list[str]
    added_urls: list[str]


def check_urls(source_text: str, translated_text: str) -> UrlCheckResult:
    source_urls = set(extract_urls(source_text))
    translated_urls = set(extract_urls(translated_text))

    missing = sorted(source_urls - translated_urls)
    added = sorted(translated_urls - source_urls)

    return UrlCheckResult(passed=not missing and not added, missing_urls=missing, added_urls=added)
