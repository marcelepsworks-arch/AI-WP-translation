# Glossary Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete FASE 5 of `PLA-ACCIO.md`: a Glossary Engine that loads domain terminology from JSON files, selects only the terms relevant to a given piece of source text (brief section 8: "el motor ha d'enviar a DeepSeek només el subconjunt del glossari rellevant"), and locally validates that mandatory terms were used correctly in a translation — independent of and complementary to `DeepSeekClient.validate_terminology()` (FASE 4.4, LLM-based check).

**Architecture:** A `GlossaryEntry` Pydantic model (loaded from `glossary/*.json`), a loader (`load_glossary_files`), and two pure functions: `get_relevant_terms()` (keyword filtering, returns `GlossaryTerm` objects already compatible with `prompt_builder`/`DeepSeekClient`) and `validate_translation()` (deterministic local check — no LLM call — that flags mandatory terms whose source concept appears in the source text but whose exact target term is missing from the translation). Seed glossary files are populated with the example terms from the brief (section 8) plus a small set of well-established GNSS/RTK/surveying terms; both files are explicitly marked as a starting point to be expanded once real site content is available (FASE 0, blocked on staging access per `MEMORIA.md`).

**Tech Stack:** Python 3.10, `pydantic` v2 (reusing patterns from `app/translation/schemas.py`), `pytest`. No network calls — this whole module is deterministic and local.

## Global Constraints

- No fabricated precision-gnss.com-specific terminology — only terms already present in the brief or well-established GNSS/RTK/surveying vocabulary, clearly marked as a seed glossary pending real-content expansion.
- `get_relevant_terms()` must return `app.translation.prompt_builder.GlossaryTerm` objects directly usable by `DeepSeekClient.translate()`/`.validate_terminology()` — no adapter layer needed elsewhere.
- `validate_translation()` is a local heuristic (substring/word matching), not a replacement for the DeepSeek-based `validate_terminology()` — it exists to catch obvious misses cheaply before spending an API call.
- Code and comments in English.

---

## File Structure

```
glossary/
├── gnss.json          # GNSS/RTK/PPK core terms
└── surveying.json      # surveying/geodesy terms

app/translation/
└── glossary.py         # GlossaryEntry, load_glossary_files(), get_relevant_terms(), validate_translation()

tests/translation/
└── test_glossary.py
```

---

### Task 1: Seed glossary JSON files

**Files:**
- Create: `glossary/gnss.json`
- Create: `glossary/surveying.json`

- [x] **Step 1: Create `glossary/gnss.json`**

```json
[
  {
    "source": "base station",
    "target": "estación base",
    "language": "es",
    "status": "mandatory",
    "notes": "GNSS/RTK context"
  },
  {
    "source": "rover",
    "target": "rover",
    "language": "es",
    "status": "mandatory",
    "notes": "Do not translate — standard term in Spanish GNSS usage"
  },
  {
    "source": "fix",
    "target": "solución fija",
    "language": "es",
    "status": "mandatory",
    "context": "RTK positioning",
    "notes": "Do not translate as 'arreglar'"
  },
  {
    "source": "float solution",
    "target": "solución flotante",
    "language": "es",
    "status": "mandatory",
    "context": "RTK positioning"
  },
  {
    "source": "baseline",
    "target": "línea base",
    "language": "es",
    "status": "mandatory",
    "context": "RTK/PPK positioning"
  },
  {
    "source": "correction stream",
    "target": "flujo de correcciones",
    "language": "es",
    "status": "mandatory",
    "context": "NTRIP/RTK"
  }
]
```

- [x] **Step 2: Create `glossary/surveying.json`**

```json
[
  {
    "source": "total station",
    "target": "estación total",
    "language": "es",
    "status": "mandatory",
    "context": "surveying"
  },
  {
    "source": "benchmark",
    "target": "punto de referencia",
    "language": "es",
    "status": "mandatory",
    "context": "geodesy"
  },
  {
    "source": "datum",
    "target": "datum",
    "language": "es",
    "status": "mandatory",
    "notes": "Do not translate — standard geodetic term"
  },
  {
    "source": "coordinate reference system",
    "target": "sistema de referencia de coordenadas",
    "language": "es",
    "status": "mandatory",
    "context": "geodesy"
  }
]
```

- [x] **Step 3: Commit**

```bash
git add glossary/gnss.json glossary/surveying.json
git commit -m "feat: add seed glossary files for GNSS/RTK and surveying terms"
```

---

### Task 2: `GlossaryEntry` model and file loader

**Files:**
- Create: `app/translation/glossary.py`
- Create: `tests/translation/test_glossary.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `GlossaryEntry(source: str, target: str, language: str, status: str, context: str = "", notes: str = "")`; `load_glossary_files(paths: list[Path]) -> list[GlossaryEntry]`. Task 3 uses both.

- [x] **Step 1: Write the failing test — `tests/translation/test_glossary.py`**

```python
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
```

- [x] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/translation/test_glossary.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.translation.glossary'`.

- [x] **Step 3: Write minimal implementation — `app/translation/glossary.py`**

```python
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
```

- [x] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/translation/test_glossary.py -v`
Expected: 2 passed.

- [x] **Step 5: Commit**

```bash
git add app/translation/glossary.py tests/translation/test_glossary.py
git commit -m "feat: add GlossaryEntry model and glossary file loader"
```

---

### Task 3: `get_relevant_terms()` — keyword filtering for DeepSeek calls

**Files:**
- Modify: `app/translation/glossary.py`
- Modify: `tests/translation/test_glossary.py`

**Interfaces:**
- Consumes: `GlossaryEntry` (Task 2), `GlossaryTerm` (from `prompt_builder`, already exists).
- Produces: `get_relevant_terms(text: str, entries: list[GlossaryEntry], language: str = "es") -> list[GlossaryTerm]`. Callers pass this list straight into `DeepSeekClient.translate(..., glossary_terms=...)`.

- [x] **Step 1: Write the failing test — append to `tests/translation/test_glossary.py`**

```python
from app.translation.glossary import get_relevant_terms
from app.translation.prompt_builder import GlossaryTerm


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
```

- [x] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest tests/translation/test_glossary.py -v`
Expected: FAIL with `ImportError: cannot import name 'get_relevant_terms'`.

- [x] **Step 3: Add `get_relevant_terms()` to `app/translation/glossary.py`**

```python
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
```

- [x] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/translation/test_glossary.py -v`
Expected: 8 passed (2 existing + 6 new).

- [x] **Step 5: Commit**

```bash
git add app/translation/glossary.py tests/translation/test_glossary.py
git commit -m "feat: add get_relevant_terms() for glossary keyword filtering"
```

---

### Task 4: `validate_translation()` — local mandatory-term check

**Files:**
- Modify: `app/translation/glossary.py`
- Modify: `tests/translation/test_glossary.py`

**Interfaces:**
- Consumes: `GlossaryEntry` (Task 2).
- Produces: `GlossaryViolation(source: str, expected_target: str)`; `validate_translation(source_text: str, translated_text: str, entries: list[GlossaryEntry], language: str = "es") -> list[GlossaryViolation]`.

- [x] **Step 1: Write the failing test — append to `tests/translation/test_glossary.py`**

```python
from app.translation.glossary import GlossaryViolation, validate_translation


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
    entries = [
        GlossaryEntry(source="rover", target="rover", language="es", status="mandatory")
    ]

    violations = validate_translation(
        source_text="The base station is powered by solar panels.",
        translated_text="La estación de referencia se alimenta con paneles solares.",
        entries=entries,
    )

    assert violations == []
```

- [x] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest tests/translation/test_glossary.py -v`
Expected: FAIL with `ImportError: cannot import name 'GlossaryViolation'`.

- [x] **Step 3: Add `GlossaryViolation` and `validate_translation()` to `app/translation/glossary.py`**

```python
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
```

- [x] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/translation/test_glossary.py -v`
Expected: 12 passed (8 existing + 4 new).

- [x] **Step 5: Run the full project test suite**

Run: `.venv/Scripts/python.exe -m pytest -v`
Expected: all tests pass (39 existing + 12 new = 51 total).

- [x] **Step 6: Commit**

```bash
git add app/translation/glossary.py tests/translation/test_glossary.py
git commit -m "feat: add validate_translation() for local mandatory-term checks"
```

---

### Task 5: Update tracking docs

**Files:**
- Modify: `PLA-ACCIO.md`
- Modify: `LOG.md`

- [x] **Step 1:** Mark `PLA-ACCIO.md` FASE 5 tasks done (5.1-5.4), note the seed-glossary caveat (pending real-content expansion once staging access exists).
- [x] **Step 2:** Add a `LOG.md` entry summarizing this session.
- [x] **Step 3: Commit**

```bash
git add PLA-ACCIO.md LOG.md docs/superpowers/plans/2026-07-23-glossary-engine.md
git commit -m "docs: mark FASE 5 done, log glossary engine session"
```

---

## Out of scope for this plan

- Wiring `get_relevant_terms()`/`validate_translation()` into an end-to-end pipeline with `DeepSeekClient` — that belongs to FASE 8 (orchestration), after WordPress content extraction exists.
- Expanding the glossary with real precision-gnss.com terminology — blocked on FASE 0 (staging access), tracked in `MEMORIA.md`.
- `spanish.json`/`forestry.json` glossary files mentioned in the original brief — not created yet since there's no confirmed real terminology to seed them with beyond guessing; add when FASE 0 audit provides real content.
