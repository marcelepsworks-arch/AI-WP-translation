"""Glossary Engine: loads domain terminology and selects the relevant
subset for a given piece of text (brief section 8), plus a local,
deterministic check for mandatory-term compliance.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from pydantic import BaseModel

from app.translation.prompt_builder import GlossaryTerm


class GlossaryEntry(BaseModel):
    source: str
    target: str
    language: str
    status: str
    context: str = ""
    notes: str = ""


def load_glossary_files(paths: list[Path]) -> list[GlossaryEntry]:
    entries: list[GlossaryEntry] = []
    for path in paths:
        raw = json.loads(path.read_text(encoding="utf-8"))
        entries.extend(GlossaryEntry.model_validate(item) for item in raw)
    return entries


def get_relevant_terms(
    text: str,
    entries: list[GlossaryEntry],
    language: str = "es",
) -> list[GlossaryTerm]:
    matches: list[GlossaryTerm] = []
    for entry in entries:
        if entry.language != language:
            continue
        pattern = r"\b" + re.escape(entry.source) + r"\b"
        if re.search(pattern, text, flags=re.IGNORECASE):
            matches.append(
                GlossaryTerm(source=entry.source, target=entry.target, notes=entry.notes)
            )
    return matches


class GlossaryViolation(BaseModel):
    source: str
    expected_target: str


def validate_translation(
    source_text: str,
    translated_text: str,
    entries: list[GlossaryEntry],
    language: str = "es",
) -> list[GlossaryViolation]:
    violations: list[GlossaryViolation] = []
    for entry in entries:
        if entry.language != language or entry.status != "mandatory":
            continue

        source_pattern = r"\b" + re.escape(entry.source) + r"\b"
        if not re.search(source_pattern, source_text, flags=re.IGNORECASE):
            continue

        target_pattern = r"\b" + re.escape(entry.target) + r"\b"
        if not re.search(target_pattern, translated_text, flags=re.IGNORECASE):
            violations.append(
                GlossaryViolation(source=entry.source, expected_target=entry.target)
            )

    return violations
