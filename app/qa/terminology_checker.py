"""Checks that protected technical terms (GNSS, RTK, NTRIP, product
codes) present in the source survive verbatim in the translation —
brief section 12.3. Case-sensitive on purpose: product codes and
acronyms must keep their exact casing.
"""
from __future__ import annotations

import re

from pydantic import BaseModel


class TerminologyCheckResult(BaseModel):
    passed: bool
    missing_terms: list[str]


def check_protected_terms(
    source_text: str,
    translated_text: str,
    protected_terms: list[str],
) -> TerminologyCheckResult:
    missing: list[str] = []

    for term in protected_terms:
        pattern = r"\b" + re.escape(term) + r"\b"
        present_in_source = re.search(pattern, source_text, re.IGNORECASE) is not None
        if not present_in_source:
            continue
        if term not in translated_text:
            missing.append(term)

    return TerminologyCheckResult(passed=len(missing) == 0, missing_terms=missing)
