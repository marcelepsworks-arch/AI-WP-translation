"""Checks that numeric values (measurements, percentages, ranges) are
preserved exactly between source and translation — brief section 12.1.
"""
from __future__ import annotations

import re

from pydantic import BaseModel

_NUMBER_PATTERN = re.compile(r"\d+(?:[.,]\d+)?")


def extract_numbers(text: str) -> list[str]:
    return _NUMBER_PATTERN.findall(text)


def _normalize(number: str) -> str:
    return number.replace(",", ".")


class NumericCheckResult(BaseModel):
    passed: bool
    source_numbers: list[str]
    translated_numbers: list[str]


def check_numbers(source_text: str, translated_text: str) -> NumericCheckResult:
    source_numbers = sorted(_normalize(n) for n in extract_numbers(source_text))
    translated_numbers = sorted(_normalize(n) for n in extract_numbers(translated_text))

    return NumericCheckResult(
        passed=source_numbers == translated_numbers,
        source_numbers=source_numbers,
        translated_numbers=translated_numbers,
    )
