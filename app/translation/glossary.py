"""Glossary Engine: loads domain terminology and selects the relevant
subset for a given piece of text (brief section 8), plus a local,
deterministic check for mandatory-term compliance.
"""
from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel


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
