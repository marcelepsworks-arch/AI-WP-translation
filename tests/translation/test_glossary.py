import json
from pathlib import Path

import pytest

from app.translation.glossary import GlossaryEntry, load_glossary_files


@pytest.fixture
def glossary_file(tmp_path: Path) -> Path:
    data = [
        {
            "source": "base station",
            "target": "estación base",
            "language": "es",
            "status": "mandatory",
            "notes": "GNSS/RTK context",
        },
        {
            "source": "rover",
            "target": "rover",
            "language": "es",
            "status": "mandatory",
        },
    ]
    file_path = tmp_path / "test_glossary.json"
    file_path.write_text(json.dumps(data), encoding="utf-8")
    return file_path


def test_load_glossary_files_parses_entries(glossary_file: Path):
    entries = load_glossary_files([glossary_file])

    assert len(entries) == 2
    assert entries[0] == GlossaryEntry(
        source="base station",
        target="estación base",
        language="es",
        status="mandatory",
        notes="GNSS/RTK context",
    )
    assert entries[1].notes == ""


def test_load_glossary_files_merges_multiple_files(tmp_path: Path):
    file_a = tmp_path / "a.json"
    file_a.write_text(
        json.dumps([{"source": "rover", "target": "rover", "language": "es", "status": "mandatory"}]),
        encoding="utf-8",
    )
    file_b = tmp_path / "b.json"
    file_b.write_text(
        json.dumps([{"source": "datum", "target": "datum", "language": "es", "status": "mandatory"}]),
        encoding="utf-8",
    )

    entries = load_glossary_files([file_a, file_b])

    assert [e.source for e in entries] == ["rover", "datum"]
