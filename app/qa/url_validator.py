"""Checks that URLs are never altered by translation — brief section 12.4."""
from __future__ import annotations

import re

from pydantic import BaseModel

_URL_PATTERN = re.compile(r"https?://\S+")


def extract_urls(text: str) -> list[str]:
    return _URL_PATTERN.findall(text)


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
