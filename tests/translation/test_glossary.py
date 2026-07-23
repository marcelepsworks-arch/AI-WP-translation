import json
from pathlib import Path

import pytest

from app.translation.glossary import (
    GlossaryEntry,
    GlossaryViolation,
    get_relevant_terms,
    load_glossary_files,
    validate_translation,
)
from app.translation.prompt_builder import GlossaryTerm


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


def test_get_relevant_terms_returns_only_matching_entries():
    entries = [
        GlossaryEntry(source="base station", target="estación base", language="es", status="mandatory"),
        GlossaryEntry(source="rover", target="rover", language="es", status="mandatory"),
    ]

    result = get_relevant_terms("The base station broadcasts corrections.", entries)

    assert result == [GlossaryTerm(source="base station", target="estación base", notes="")]


def test_get_relevant_terms_is_case_insensitive():
    entries = [GlossaryEntry(source="Rover", target="rover", language="es", status="mandatory")]

    result = get_relevant_terms("The ROVER receives corrections.", entries)

    assert len(result) == 1
    assert result[0].source == "Rover"


def test_get_relevant_terms_matches_whole_words_only():
    entries = [GlossaryEntry(source="fix", target="solución fija", language="es", status="mandatory")]

    result = get_relevant_terms("Please fix the prefix and suffix issues.", entries)

    # "fix" must match standalone, not inside "prefix"/"suffix"
    assert len(result) == 1


def test_get_relevant_terms_filters_by_language():
    entries = [
        GlossaryEntry(source="rover", target="rover", language="es", status="mandatory"),
        GlossaryEntry(source="rover", target="véhicule mobile", language="fr", status="mandatory"),
    ]

    result = get_relevant_terms("The rover is mobile.", entries, language="fr")

    assert result == [GlossaryTerm(source="rover", target="véhicule mobile", notes="")]


def test_get_relevant_terms_includes_notes_in_glossary_term():
    entries = [
        GlossaryEntry(
            source="base station",
            target="estación base",
            language="es",
            status="mandatory",
            notes="GNSS/RTK context",
        )
    ]

    result = get_relevant_terms("base station", entries)

    assert result[0].notes == "GNSS/RTK context"


def test_get_relevant_terms_returns_empty_list_when_nothing_matches():
    entries = [GlossaryEntry(source="rover", target="rover", language="es", status="mandatory")]

    result = get_relevant_terms("This text mentions none of the terms.", entries)

    assert result == []


def test_validate_translation_flags_missing_mandatory_term():
    entries = [
        GlossaryEntry(source="base station", target="estación base", language="es", status="mandatory")
    ]

    violations = validate_translation(
        source_text="The base station is powered by solar panels.",
        translated_text="La estación de referencia se alimenta con paneles solares.",
        entries=entries,
    )

    assert violations == [GlossaryViolation(source="base station", expected_target="estación base")]


def test_validate_translation_passes_when_mandatory_term_present():
    entries = [
        GlossaryEntry(source="base station", target="estación base", language="es", status="mandatory")
    ]

    violations = validate_translation(
        source_text="The base station is powered by solar panels.",
        translated_text="La estación base se alimenta con paneles solares.",
        entries=entries,
    )

    assert violations == []


def test_validate_translation_ignores_optional_terms():
    entries = [
        GlossaryEntry(source="base station", target="estación base", language="es", status="optional")
    ]

    violations = validate_translation(
        source_text="The base station is powered by solar panels.",
        translated_text="La estación de referencia se alimenta con paneles solares.",
        entries=entries,
    )

    assert violations == []


def test_validate_translation_ignores_terms_not_present_in_source():
    entries = [GlossaryEntry(source="rover", target="rover", language="es", status="mandatory")]

    violations = validate_translation(
        source_text="The base station is powered by solar panels.",
        translated_text="La estación de referencia se alimenta con paneles solares.",
        entries=entries,
    )

    assert violations == []
