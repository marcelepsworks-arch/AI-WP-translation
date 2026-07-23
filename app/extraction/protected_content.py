"""Detects text that must never be sent for translation as-is: bare
URLs, email addresses, WordPress shortcodes, and empty text.

Matches the "protected content" rules in the project brief, section 7.2.
Does NOT flag prose containing a technical term or product name — that
is the glossary's job (app/translation/glossary.py), not extraction's.
"""
from __future__ import annotations

import re

_URL_PATTERN = re.compile(r"^(https?://|www\.)\S+$", re.IGNORECASE)
_EMAIL_PATTERN = re.compile(r"^[\w.+-]+@[\w-]+\.[\w.-]+$")
_SHORTCODE_PATTERN = re.compile(r"^\[.+\]$")


def is_protected_content(text: str) -> bool:
    stripped = text.strip()

    if not stripped:
        return True
    if _URL_PATTERN.match(stripped):
        return True
    if _EMAIL_PATTERN.match(stripped):
        return True
    if _SHORTCODE_PATTERN.match(stripped):
        return True

    return False
