# DeepSeek Translation Client Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first working, testable slice of the GNSS AI Translation Engine: a Python module that sends technical GNSS/RTK content to DeepSeek and gets back a validated, structured (JSON-mode) translation — matching the strict-fidelity system prompt and response schema defined in the project brief (`brief_gnss_translation_engine_precision_gnss.pdf`, sections 9-11).

**Architecture:** Four small, independently testable units, per `ROADMAP.md` FASE 4: `settings` (env config loading), `schemas` (Pydantic models for the DeepSeek JSON response), `prompt_builder` (builds the system prompt with the brief's translation rules + optional glossary terms), and `deepseek_client` (wraps the OpenAI-compatible SDK pointed at DeepSeek's API, calls JSON mode, validates the response against the schema). This slice deliberately excludes WordPress/WPML/Elementor integration (those require live staging credentials not yet available — see `MEMORIA.md` "Supòsits pendents") and excludes the Reviewer/Terminology Validator calls (`ROADMAP.md` FASE 4.4, separate future plan) — only the Translator call (brief section 9.A) is in scope here.

**Tech Stack:** Python 3.10, `openai` SDK (OpenAI-compatible client pointed at `https://api.deepseek.com`, per `BIBLIOGRAFIA.md` §8), `pydantic` v2 for response validation, `pytest` + `pytest-mock` for tests, `python-dotenv` for local `.env` loading.

## Global Constraints

- No live calls to the real DeepSeek API in the automated test suite — all HTTP/SDK interaction is mocked. A real API key is only needed for manual smoke testing.
- Match the brief's system prompt rules (section 10) verbatim in content — the 15 MUST rules and 5 MUST NOT rules — parameterized only by target language name and glossary terms.
- Match the brief's response schema (section 11) exactly: `translation` (str), `confidence` (float 0-1), `issues` (list of `{type, description}`), `terminology_used` (list of `{source, target}`).
- `DEEPSEEK_API_KEY` must never be hardcoded — always read from environment (`.env`, not committed).
- Code and comments in English (per project CLAUDE.md instructions), even though planning docs are in Catalan.

---

## File Structure

```
AI-WP-translation/
├── app/
│   ├── __init__.py
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py          # load_settings() -> Settings
│   └── translation/
│       ├── __init__.py
│       ├── schemas.py           # TranslationResult, TranslationIssue, TerminologyUsed
│       ├── prompt_builder.py    # build_system_prompt(), GlossaryTerm
│       └── deepseek_client.py   # DeepSeekClient.translate()
├── tests/
│   ├── __init__.py
│   ├── config/
│   │   ├── __init__.py
│   │   └── test_settings.py
│   └── translation/
│       ├── __init__.py
│       ├── test_schemas.py
│       ├── test_prompt_builder.py
│       └── test_deepseek_client.py
├── scripts/
│   └── translate_sample.py      # manual smoke-test entry point (real API call)
├── requirements.txt
├── .env.example
└── pytest.ini
```

---

### Task 1: Project scaffold + settings loader

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `pytest.ini`
- Create: `app/__init__.py`
- Create: `app/config/__init__.py`
- Create: `app/config/settings.py`
- Create: `tests/__init__.py`
- Create: `tests/config/__init__.py`
- Create: `tests/config/test_settings.py`

**Interfaces:**
- Produces: `Settings` dataclass with fields `deepseek_api_key: str`, `deepseek_base_url: str`, `default_model: str`, `qa_model: str`, `source_language: str`, `target_languages: list[str]`.
- Produces: `load_settings(env: dict[str, str] | None = None) -> Settings`.

- [ ] **Step 1: Create `requirements.txt`**

```
openai>=1.40.0
pydantic>=2.7.0
python-dotenv>=1.0.0
pytest>=8.0.0
pytest-mock>=3.14.0
```

- [ ] **Step 2: Create `.env.example`**

```
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEFAULT_MODEL=deepseek-v4-pro
QA_MODEL=deepseek-v4-pro
SOURCE_LANGUAGE=en
TARGET_LANGUAGES=es
```

- [ ] **Step 3: Create `pytest.ini`**

```ini
[pytest]
testpaths = tests
python_files = test_*.py
```

- [ ] **Step 4: Create package init files**

`app/__init__.py`:
```python
```

`app/config/__init__.py`:
```python
```

`tests/__init__.py`:
```python
```

`tests/config/__init__.py`:
```python
```

- [ ] **Step 5: Write the failing test — `tests/config/test_settings.py`**

```python
import pytest

from app.config.settings import Settings, load_settings


def test_load_settings_reads_all_fields_from_env():
    env = {
        "DEEPSEEK_API_KEY": "test-key-123",
        "DEEPSEEK_BASE_URL": "https://api.deepseek.com",
        "DEFAULT_MODEL": "deepseek-v4-pro",
        "QA_MODEL": "deepseek-v4-flash",
        "SOURCE_LANGUAGE": "en",
        "TARGET_LANGUAGES": "es,fr,de",
    }

    settings = load_settings(env)

    assert settings == Settings(
        deepseek_api_key="test-key-123",
        deepseek_base_url="https://api.deepseek.com",
        default_model="deepseek-v4-pro",
        qa_model="deepseek-v4-flash",
        source_language="en",
        target_languages=["es", "fr", "de"],
    )


def test_load_settings_applies_defaults_when_optional_fields_missing():
    env = {"DEEPSEEK_API_KEY": "test-key-123"}

    settings = load_settings(env)

    assert settings.deepseek_base_url == "https://api.deepseek.com"
    assert settings.default_model == "deepseek-v4-pro"
    assert settings.qa_model == "deepseek-v4-pro"
    assert settings.source_language == "en"
    assert settings.target_languages == ["es"]


def test_load_settings_raises_when_api_key_missing():
    with pytest.raises(ValueError, match="DEEPSEEK_API_KEY"):
        load_settings({})


def test_load_settings_strips_whitespace_from_target_languages():
    env = {"DEEPSEEK_API_KEY": "k", "TARGET_LANGUAGES": " es , fr ,de "}

    settings = load_settings(env)

    assert settings.target_languages == ["es", "fr", "de"]
```

- [ ] **Step 6: Run test to verify it fails**

Run: `python -m pytest tests/config/test_settings.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.config.settings'` (or similar import error).

- [ ] **Step 7: Write minimal implementation — `app/config/settings.py`**

```python
"""Environment-based configuration loading for the translation engine."""
from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    deepseek_api_key: str
    deepseek_base_url: str = "https://api.deepseek.com"
    default_model: str = "deepseek-v4-pro"
    qa_model: str = "deepseek-v4-pro"
    source_language: str = "en"
    target_languages: list[str] = field(default_factory=lambda: ["es"])


def load_settings(env: dict[str, str] | None = None) -> Settings:
    """Load Settings from a mapping of environment variables.

    Pass an explicit `env` dict in tests; defaults to `os.environ` at runtime.
    """
    source = env if env is not None else os.environ

    api_key = source.get("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY is required but was not set")

    target_languages_raw = source.get("TARGET_LANGUAGES", "es")
    target_languages = [
        lang.strip() for lang in target_languages_raw.split(",") if lang.strip()
    ]

    return Settings(
        deepseek_api_key=api_key,
        deepseek_base_url=source.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        default_model=source.get("DEFAULT_MODEL", "deepseek-v4-pro"),
        qa_model=source.get("QA_MODEL", "deepseek-v4-pro"),
        source_language=source.get("SOURCE_LANGUAGE", "en"),
        target_languages=target_languages,
    )
```

- [ ] **Step 8: Run test to verify it passes**

Run: `python -m pytest tests/config/test_settings.py -v`
Expected: 4 passed.

- [ ] **Step 9: Commit**

```bash
git add requirements.txt .env.example pytest.ini app/__init__.py app/config/__init__.py app/config/settings.py tests/__init__.py tests/config/__init__.py tests/config/test_settings.py
git commit -m "feat: add settings loader for DeepSeek/translation config"
```

---

### Task 2: Response schema (Pydantic models)

**Files:**
- Create: `app/translation/__init__.py`
- Create: `app/translation/schemas.py`
- Create: `tests/translation/__init__.py`
- Create: `tests/translation/test_schemas.py`

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces: `TerminologyUsed(source: str, target: str)`, `TranslationIssue(type: str, description: str)`, `TranslationResult(translation: str, confidence: float, issues: list[TranslationIssue], terminology_used: list[TerminologyUsed])`. `TranslationResult.model_validate(dict)` is the entry point later tasks use to parse the raw DeepSeek JSON response.

- [ ] **Step 1: Create `app/translation/__init__.py`**

```python
```

- [ ] **Step 2: Create `tests/translation/__init__.py`**

```python
```

- [ ] **Step 3: Write the failing test — `tests/translation/test_schemas.py`**

```python
import pytest
from pydantic import ValidationError

from app.translation.schemas import TranslationIssue, TranslationResult


def test_translation_result_parses_full_valid_payload():
    payload = {
        "translation": "Estación base de alta precisión",
        "confidence": 0.96,
        "issues": [],
        "terminology_used": [
            {"source": "base station", "target": "estación base"}
        ],
    }

    result = TranslationResult.model_validate(payload)

    assert result.translation == "Estación base de alta precisión"
    assert result.confidence == 0.96
    assert result.issues == []
    assert result.terminology_used[0].source == "base station"
    assert result.terminology_used[0].target == "estación base"


def test_translation_result_parses_payload_with_issues():
    payload = {
        "translation": "...",
        "confidence": 0.71,
        "issues": [
            {
                "type": "technical_ambiguity",
                "description": "The source term may have two technical interpretations.",
            }
        ],
        "terminology_used": [],
    }

    result = TranslationResult.model_validate(payload)

    assert len(result.issues) == 1
    assert isinstance(result.issues[0], TranslationIssue)
    assert result.issues[0].type == "technical_ambiguity"


def test_translation_result_defaults_issues_and_terminology_to_empty_list():
    payload = {"translation": "text", "confidence": 0.9}

    result = TranslationResult.model_validate(payload)

    assert result.issues == []
    assert result.terminology_used == []


@pytest.mark.parametrize("bad_confidence", [-0.1, 1.1, 2.0])
def test_translation_result_rejects_confidence_out_of_range(bad_confidence):
    payload = {"translation": "text", "confidence": bad_confidence}

    with pytest.raises(ValidationError):
        TranslationResult.model_validate(payload)


def test_translation_result_requires_translation_field():
    with pytest.raises(ValidationError):
        TranslationResult.model_validate({"confidence": 0.9})
```

- [ ] **Step 4: Run test to verify it fails**

Run: `python -m pytest tests/translation/test_schemas.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.translation.schemas'`.

- [ ] **Step 5: Write minimal implementation — `app/translation/schemas.py`**

```python
"""Structured response schema for DeepSeek translation calls.

Matches the JSON contract defined in the project brief, section 11:
{"translation": "...", "confidence": 0.96, "issues": [...], "terminology_used": [...]}
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class TerminologyUsed(BaseModel):
    source: str
    target: str


class TranslationIssue(BaseModel):
    type: str
    description: str


class TranslationResult(BaseModel):
    translation: str
    confidence: float = Field(ge=0.0, le=1.0)
    issues: list[TranslationIssue] = Field(default_factory=list)
    terminology_used: list[TerminologyUsed] = Field(default_factory=list)
```

- [ ] **Step 6: Run test to verify it passes**

Run: `python -m pytest tests/translation/test_schemas.py -v`
Expected: 5 passed.

- [ ] **Step 7: Commit**

```bash
git add app/translation/__init__.py app/translation/schemas.py tests/translation/__init__.py tests/translation/test_schemas.py
git commit -m "feat: add Pydantic schema for DeepSeek translation responses"
```

---

### Task 3: System prompt builder

**Files:**
- Create: `app/translation/prompt_builder.py`
- Create: `tests/translation/test_prompt_builder.py`

**Interfaces:**
- Consumes: nothing from Tasks 1-2 (pure string building).
- Produces: `GlossaryTerm(source: str, target: str, notes: str = "")`; `build_system_prompt(target_language_name: str, glossary_terms: list[GlossaryTerm] | None = None) -> str`. Task 4 calls this to build the `system` message.

- [ ] **Step 1: Write the failing test — `tests/translation/test_prompt_builder.py`**

```python
from app.translation.prompt_builder import GlossaryTerm, build_system_prompt


def test_prompt_mentions_target_language():
    prompt = build_system_prompt("European Spanish")

    assert "European Spanish" in prompt


def test_prompt_includes_core_fidelity_rules():
    prompt = build_system_prompt("European Spanish")

    assert "Preserve the exact meaning of the source" in prompt
    assert "Preserve numerical values and units exactly" in prompt
    assert "Never invent information" in prompt
    assert "Return valid structured JSON" in prompt


def test_prompt_includes_must_not_rules():
    prompt = build_system_prompt("European Spanish")

    assert "simplify technical language" in prompt
    assert "translate protected product names" in prompt


def test_prompt_has_no_glossary_section_when_no_terms_given():
    prompt = build_system_prompt("European Spanish")

    assert "MANDATORY GLOSSARY" not in prompt


def test_prompt_includes_glossary_terms_when_given():
    terms = [
        GlossaryTerm(source="base station", target="estación base", notes="GNSS/RTK context"),
        GlossaryTerm(source="rover", target="rover"),
    ]

    prompt = build_system_prompt("European Spanish", terms)

    assert "MANDATORY GLOSSARY" in prompt
    assert "base station -> estación base" in prompt
    assert "GNSS/RTK context" in prompt
    assert "rover -> rover" in prompt
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/translation/test_prompt_builder.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.translation.prompt_builder'`.

- [ ] **Step 3: Write minimal implementation — `app/translation/prompt_builder.py`**

```python
"""Builds the DeepSeek system prompt for technical GNSS/RTK translation.

Rule text is taken verbatim from the project brief, section 10, and
parameterized only by target language and an optional glossary subset
(brief section 8: only the relevant glossary terms are sent per call).
"""
from __future__ import annotations

from dataclasses import dataclass

_DOMAIN_EXPERTISE = """You are a senior technical translator specialized in:
- GNSS
- RTK positioning
- PPK
- surveying
- geodesy
- precision agriculture
- forestry
- machine control
- autonomous systems
- industrial positioning
- maritime navigation"""

_MUST_RULES = """You MUST:
1. Preserve the exact meaning of the source.
2. Preserve all technical qualifications and limitations.
3. Preserve numerical values and units exactly.
4. Preserve technical distinctions between concepts.
5. Use the terminology glossary exactly.
6. Preserve product names and model numbers.
7. Never invent information.
8. Never add explanations.
9. Never remove technical information.
10. Never improve or reinterpret the technical claim.
11. Preserve the same degree of certainty.
12. Preserve conditional statements.
13. Preserve warnings and limitations.
14. Preserve URLs and placeholders.
15. Return valid structured JSON."""

_MUST_NOT_RULES = """You MUST NOT:
- simplify technical language;
- make claims stronger;
- make claims weaker;
- replace technical terms with generic marketing language;
- translate protected product names;
- translate acronyms unless explicitly instructed."""

_AMBIGUITY_RULE = (
    "If a source sentence is technically ambiguous, preserve the ambiguity "
    "and do not invent an interpretation."
)

_RESPONSE_FORMAT_RULE = """Respond ONLY with a JSON object matching this exact shape:
{"translation": "...", "confidence": 0.0-1.0, "issues": [{"type": "...", "description": "..."}], "terminology_used": [{"source": "...", "target": "..."}]}"""


@dataclass(frozen=True)
class GlossaryTerm:
    source: str
    target: str
    notes: str = ""


def _build_glossary_section(glossary_terms: list[GlossaryTerm]) -> str:
    lines = ["MANDATORY GLOSSARY — use these translations exactly:"]
    for term in glossary_terms:
        line = f"- {term.source} -> {term.target}"
        if term.notes:
            line += f" ({term.notes})"
        lines.append(line)
    return "\n".join(lines)


def build_system_prompt(
    target_language_name: str,
    glossary_terms: list[GlossaryTerm] | None = None,
) -> str:
    sections = [
        _DOMAIN_EXPERTISE,
        f"You translate from English to {target_language_name}.",
        "Your primary objective is semantic fidelity.",
        _MUST_RULES,
        _MUST_NOT_RULES,
        _AMBIGUITY_RULE,
    ]

    if glossary_terms:
        sections.append(_build_glossary_section(glossary_terms))

    sections.append(_RESPONSE_FORMAT_RULE)

    return "\n\n".join(sections)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/translation/test_prompt_builder.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add app/translation/prompt_builder.py tests/translation/test_prompt_builder.py
git commit -m "feat: add DeepSeek system prompt builder with glossary injection"
```

---

### Task 4: DeepSeek client (the actual API call)

**Files:**
- Create: `app/translation/deepseek_client.py`
- Create: `tests/translation/test_deepseek_client.py`

**Interfaces:**
- Consumes: `build_system_prompt(target_language_name, glossary_terms)` from Task 3; `TranslationResult.model_validate(dict)` from Task 2; `Settings` from Task 1 (for `deepseek_api_key`, `deepseek_base_url`, `default_model`).
- Produces: `DeepSeekClient(api_key: str, base_url: str = "https://api.deepseek.com", model: str = "deepseek-v4-pro", client: OpenAI | None = None)` with method `translate(source_text: str, target_language_name: str, context: str = "", glossary_terms: list[GlossaryTerm] | None = None) -> TranslationResult`. The `client` constructor param exists purely so tests can inject a fake — production code never passes it.

- [ ] **Step 1: Write the failing test — `tests/translation/test_deepseek_client.py`**

```python
import json
from unittest.mock import MagicMock

from app.translation.deepseek_client import DeepSeekClient
from app.translation.prompt_builder import GlossaryTerm
from app.translation.schemas import TranslationResult


def _fake_openai_client(response_payload: dict) -> MagicMock:
    fake_client = MagicMock()
    fake_message = MagicMock()
    fake_message.content = json.dumps(response_payload)
    fake_choice = MagicMock()
    fake_choice.message = fake_message
    fake_response = MagicMock()
    fake_response.choices = [fake_choice]
    fake_client.chat.completions.create.return_value = fake_response
    return fake_client


def test_translate_returns_parsed_translation_result():
    payload = {
        "translation": "Estación base",
        "confidence": 0.95,
        "issues": [],
        "terminology_used": [{"source": "base station", "target": "estación base"}],
    }
    fake_client = _fake_openai_client(payload)

    client = DeepSeekClient(api_key="test-key", client=fake_client)
    result = client.translate("base station", target_language_name="European Spanish")

    assert isinstance(result, TranslationResult)
    assert result.translation == "Estación base"
    assert result.confidence == 0.95


def test_translate_calls_api_with_json_mode_and_correct_model():
    fake_client = _fake_openai_client({"translation": "x", "confidence": 0.9})

    client = DeepSeekClient(api_key="test-key", model="deepseek-v4-pro", client=fake_client)
    client.translate("hello", target_language_name="European Spanish")

    fake_client.chat.completions.create.assert_called_once()
    _, kwargs = fake_client.chat.completions.create.call_args
    assert kwargs["model"] == "deepseek-v4-pro"
    assert kwargs["response_format"] == {"type": "json_object"}
    assert kwargs["messages"][0]["role"] == "system"
    assert kwargs["messages"][1]["role"] == "user"
    assert "hello" in kwargs["messages"][1]["content"]


def test_translate_includes_context_in_user_message_when_given():
    fake_client = _fake_openai_client({"translation": "x", "confidence": 0.9})

    client = DeepSeekClient(api_key="test-key", client=fake_client)
    client.translate(
        "hello",
        target_language_name="European Spanish",
        context="RTK Applications > Archaeology",
    )

    _, kwargs = fake_client.chat.completions.create.call_args
    user_message = kwargs["messages"][1]["content"]
    assert "RTK Applications > Archaeology" in user_message
    assert "hello" in user_message


def test_translate_passes_glossary_terms_into_system_prompt():
    fake_client = _fake_openai_client({"translation": "x", "confidence": 0.9})
    terms = [GlossaryTerm(source="rover", target="rover")]

    client = DeepSeekClient(api_key="test-key", client=fake_client)
    client.translate("hello", target_language_name="European Spanish", glossary_terms=terms)

    _, kwargs = fake_client.chat.completions.create.call_args
    system_message = kwargs["messages"][0]["content"]
    assert "rover -> rover" in system_message


def test_client_constructs_openai_client_with_base_url_when_not_injected():
    client = DeepSeekClient(api_key="test-key", base_url="https://api.deepseek.com")

    assert client._client.base_url is not None
    assert "api.deepseek.com" in str(client._client.base_url)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/translation/test_deepseek_client.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.translation.deepseek_client'`.

- [ ] **Step 3: Write minimal implementation — `app/translation/deepseek_client.py`**

```python
"""Client for calling DeepSeek's OpenAI-compatible chat completions API
to translate technical GNSS/RTK content.

DeepSeek's API is OpenAI-compatible (base_url swap only) and supports
JSON mode for structured output — see BIBLIOGRAFIA.md section 8.
"""
from __future__ import annotations

import json

from openai import OpenAI

from app.translation.prompt_builder import GlossaryTerm, build_system_prompt
from app.translation.schemas import TranslationResult


class DeepSeekClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com",
        model: str = "deepseek-v4-pro",
        client: OpenAI | None = None,
    ) -> None:
        self._model = model
        self._client = client or OpenAI(api_key=api_key, base_url=base_url)

    def translate(
        self,
        source_text: str,
        target_language_name: str,
        context: str = "",
        glossary_terms: list[GlossaryTerm] | None = None,
    ) -> TranslationResult:
        system_prompt = build_system_prompt(target_language_name, glossary_terms)
        user_prompt = self._build_user_prompt(source_text, context)

        response = self._client.chat.completions.create(
            model=self._model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        raw_content = response.choices[0].message.content
        data = json.loads(raw_content)
        return TranslationResult.model_validate(data)

    @staticmethod
    def _build_user_prompt(source_text: str, context: str) -> str:
        if context:
            return f"Context: {context}\n\nText to translate:\n{source_text}"
        return f"Text to translate:\n{source_text}"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/translation/test_deepseek_client.py -v`
Expected: 5 passed.

- [ ] **Step 5: Run the full test suite**

Run: `python -m pytest -v`
Expected: all tests from Tasks 1-4 pass (19 tests total).

- [ ] **Step 6: Commit**

```bash
git add app/translation/deepseek_client.py tests/translation/test_deepseek_client.py
git commit -m "feat: add DeepSeekClient with JSON-mode structured translation"
```

---

### Task 5: Manual smoke-test script

**Files:**
- Create: `scripts/translate_sample.py`

**Interfaces:**
- Consumes: `load_settings()` (Task 1), `DeepSeekClient` (Task 4). No new interfaces produced — this is a thin CLI entry point, not imported by other code.

- [ ] **Step 1: Create `scripts/translate_sample.py`**

```python
"""Manual smoke test: translate one hardcoded technical sentence via DeepSeek.

Usage:
    DEEPSEEK_API_KEY=sk-... python scripts/translate_sample.py

This makes a REAL API call and costs real tokens — do not run in CI.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

from app.config.settings import load_settings
from app.translation.deepseek_client import DeepSeekClient
from app.translation.prompt_builder import GlossaryTerm

SAMPLE_TEXT = (
    "The ZED-F9P module delivers 1 cm RTK accuracy when connected to a "
    "base station over NTRIP, provided the baseline distance stays below 10 km."
)

GLOSSARY = [
    GlossaryTerm(source="base station", target="estación base", notes="GNSS/RTK context"),
    GlossaryTerm(source="RTK", target="RTK"),
]


def main() -> None:
    load_dotenv()
    settings = load_settings()

    client = DeepSeekClient(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        model=settings.default_model,
    )

    result = client.translate(
        SAMPLE_TEXT,
        target_language_name="European Spanish",
        context="RTK Applications > Product Specifications",
        glossary_terms=GLOSSARY,
    )

    print(f"Source:     {SAMPLE_TEXT}")
    print(f"Translation: {result.translation}")
    print(f"Confidence:  {result.confidence}")
    print(f"Issues:      {result.issues}")
    print(f"Terminology: {result.terminology_used}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify the script is syntactically valid (does not run it — no API key required for this check)**

Run: `python -m py_compile scripts/translate_sample.py`
Expected: no output, exit code 0.

- [ ] **Step 3: Commit**

```bash
git add scripts/translate_sample.py
git commit -m "chore: add manual smoke-test script for DeepSeek translation"
```

---

## Out of scope for this plan (tracked in ROADMAP.md / PLA-ACCIO.md for later plans)

- Technical Reviewer and Terminology Validator DeepSeek calls (brief section 9.B/9.C) — FASE 4.4.
- Glossary loading from `glossary/*.json` files and `get_relevant_terms()` filtering — FASE 5.
- WordPress connector, `gnss-bridge` mu-plugin, Elementor extraction, QA engine, Translation Memory — FASES 1-3, 6-8, all blocked on live staging credentials per `MEMORIA.md`.
