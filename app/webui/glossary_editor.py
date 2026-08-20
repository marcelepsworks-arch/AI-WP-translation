"""Read/write access to the existing glossary JSON files for the dashboard.

No new storage and no new schema: these are the same
`glossary/gnss.json` and `glossary/surveying.json` that
`app.translation.glossary` already loads, in the same shape. The only
thing added is a safe way to edit them without opening a text editor.

Every write is validated against `GlossaryEntry` first and then staged
through a temporary file, because these files feed every translation --
a glossary left half-written by a crashed request would poison every run
after it.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from pydantic import ValidationError

from app.translation.glossary import GlossaryEntry


def read_glossary(path: Path) -> list[dict]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return [GlossaryEntry.model_validate(item).model_dump() for item in raw]


def write_glossary(path: Path, entries: list[dict]) -> list[dict]:
    """Validates every entry before touching the file. Raises ValueError on
    the first invalid one, leaving the existing glossary exactly as it was.
    """
    try:
        validated = [GlossaryEntry.model_validate(entry) for entry in entries]
    except ValidationError as exc:
        raise ValueError(f"invalid glossary entry: {exc.errors()[0]['msg']}") from exc

    path = Path(path)
    payload = json.dumps([entry.model_dump() for entry in validated], ensure_ascii=False, indent=2)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(payload + "\n", encoding="utf-8")
    os.replace(temp_path, path)  # atomic: readers see either the old file or the new one
    return [entry.model_dump() for entry in validated]
