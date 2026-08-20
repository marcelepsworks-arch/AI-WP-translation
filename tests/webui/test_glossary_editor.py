import json

import pytest

from app.webui.glossary_editor import read_glossary, write_glossary

ENTRY = {
    "source": "automatic steering",
    "target": "conducción autónoma",
    "language": "es",
    "status": "mandatory",
    "context": "precision agriculture",
    "notes": "",
}


def _glossary(tmp_path, entries):
    path = tmp_path / "gnss.json"
    path.write_text(json.dumps(entries, ensure_ascii=False), encoding="utf-8")
    return path


def test_reading_returns_the_entries_as_written(tmp_path):
    path = _glossary(tmp_path, [ENTRY])

    assert read_glossary(path) == [ENTRY]


def test_writing_round_trips_through_reading(tmp_path):
    path = _glossary(tmp_path, [])

    write_glossary(path, [ENTRY])

    assert read_glossary(path) == [ENTRY]


def test_written_files_stay_human_editable_utf8_json(tmp_path):
    path = _glossary(tmp_path, [])

    write_glossary(path, [ENTRY])

    raw = path.read_text(encoding="utf-8")
    assert "conducción autónoma" in raw  # not \u-escaped
    assert raw.startswith("[\n")  # indented, reviewable in a diff


def test_an_invalid_entry_is_rejected_before_anything_is_written(tmp_path):
    path = _glossary(tmp_path, [ENTRY])

    with pytest.raises(ValueError):
        write_glossary(path, [{"source": "only a source"}])

    # The original file must survive a rejected write untouched: this file
    # feeds every translation, so a half-written glossary is worse than none.
    assert read_glossary(path) == [ENTRY]


def test_optional_fields_default_to_empty(tmp_path):
    path = _glossary(tmp_path, [])

    write_glossary(path, [{"source": "RTK", "target": "RTK", "language": "es", "status": "protected"}])

    assert read_glossary(path)[0]["context"] == ""
    assert read_glossary(path)[0]["notes"] == ""
