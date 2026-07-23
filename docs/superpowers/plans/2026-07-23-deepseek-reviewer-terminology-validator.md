# DeepSeek Reviewer & Terminology Validator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete FASE 4.4 of `PLA-ACCIO.md`: add the two remaining DeepSeek calls from the brief's translation mechanics (section 9) — the **Technical Reviewer** (compares source vs. translation, flags added/removed/altered information) and the **Terminology Validator** (audits mandatory glossary compliance) — as separate, independent calls from the Translator built in the previous plan.

**Architecture:** Extend the existing `app/translation/` module (built in `2026-07-23-deepseek-translation-client.md`) with two new response schemas, two new prompt builders, and two new methods on `DeepSeekClient`. Each call is independent (brief section 9: "no és recomanable fer una única petició que demani simultàniament traduir i revisar") and can use a different model (`qa_model` vs. the translator's `model`), matching the `.env` config already defined in `Settings` (`DEFAULT_MODEL` / `QA_MODEL`).

**Tech Stack:** Same as the prior plan — Python 3.10, `openai` SDK (JSON mode), `pydantic` v2, `pytest` + mocked HTTP (no live API calls in tests).

## Global Constraints

- No live calls to the real DeepSeek API in the automated test suite.
- Reviewer and Terminology Validator are separate calls from the Translator — never combined into one request (brief section 9).
- `DeepSeekClient` must support a distinct `qa_model` from the translation `model`, since `Settings` already exposes both.
- Code and comments in English.

---

## File Structure

```
app/translation/
├── schemas.py           # ADD: ReviewResult, TerminologyViolation, TerminologyValidationResult
├── prompt_builder.py     # ADD: build_reviewer_system_prompt(), build_terminology_validator_system_prompt()
└── deepseek_client.py    # MODIFY: add qa_model param, review(), validate_terminology()

tests/translation/
├── test_schemas.py           # ADD: tests for new models
├── test_prompt_builder.py    # ADD: tests for new prompt builders
└── test_deepseek_client.py   # ADD: tests for review() and validate_terminology()
```

---

### Task 1: Reviewer and Terminology Validator response schemas

**Files:**
- Modify: `app/translation/schemas.py`
- Modify: `tests/translation/test_schemas.py`

**Interfaces:**
- Consumes: `TranslationIssue` (already defined in `schemas.py`, reused for reviewer issues).
- Produces: `ReviewResult(passed: bool, issues: list[TranslationIssue])`; `TerminologyViolation(term: str, expected: str, found_as: str, note: str = "")`; `TerminologyValidationResult(compliant: bool, violations: list[TerminologyViolation])`. Task 3 (`deepseek_client.py`) parses raw JSON into these via `.model_validate()`.

- [x] **Step 1: Write the failing tests — append to `tests/translation/test_schemas.py`**

```python
from app.translation.schemas import (
    ReviewResult,
    TerminologyValidationResult,
    TerminologyViolation,
)


def test_review_result_parses_passing_payload():
    payload = {"passed": True, "issues": []}

    result = ReviewResult.model_validate(payload)

    assert result.passed is True
    assert result.issues == []


def test_review_result_parses_failing_payload_with_issues():
    payload = {
        "passed": False,
        "issues": [
            {"type": "information_added", "description": "Translation adds a claim not present in source."}
        ],
    }

    result = ReviewResult.model_validate(payload)

    assert result.passed is False
    assert result.issues[0].type == "information_added"


def test_review_result_defaults_issues_to_empty_list():
    result = ReviewResult.model_validate({"passed": True})

    assert result.issues == []


def test_terminology_validation_result_parses_compliant_payload():
    result = TerminologyValidationResult.model_validate({"compliant": True, "violations": []})

    assert result.compliant is True
    assert result.violations == []


def test_terminology_validation_result_parses_violations():
    payload = {
        "compliant": False,
        "violations": [
            {
                "term": "base station",
                "expected": "estación base",
                "found_as": "estación de referencia",
                "note": "Inconsistent with mandatory glossary",
            }
        ],
    }

    result = TerminologyValidationResult.model_validate(payload)

    assert result.compliant is False
    assert isinstance(result.violations[0], TerminologyViolation)
    assert result.violations[0].term == "base station"
    assert result.violations[0].found_as == "estación de referencia"


def test_terminology_validation_result_defaults_violations_to_empty_list():
    result = TerminologyValidationResult.model_validate({"compliant": True})

    assert result.violations == []
```

- [x] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest tests/translation/test_schemas.py -v`
Expected: FAIL with `ImportError: cannot import name 'ReviewResult' from 'app.translation.schemas'`.

- [x] **Step 3: Add the new models to `app/translation/schemas.py`**

Append after the existing `TranslationResult` class:

```python
class ReviewResult(BaseModel):
    passed: bool
    issues: list[TranslationIssue] = Field(default_factory=list)


class TerminologyViolation(BaseModel):
    term: str
    expected: str
    found_as: str
    note: str = ""


class TerminologyValidationResult(BaseModel):
    compliant: bool
    violations: list[TerminologyViolation] = Field(default_factory=list)
```

- [x] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/translation/test_schemas.py -v`
Expected: 12 passed (7 existing + 5 new... note: 6 new tests above, so 13 passed).

- [x] **Step 5: Commit**

```bash
git add app/translation/schemas.py tests/translation/test_schemas.py
git commit -m "feat: add ReviewResult and TerminologyValidationResult schemas"
```

---

### Task 2: Reviewer and Terminology Validator prompt builders

**Files:**
- Modify: `app/translation/prompt_builder.py`
- Modify: `tests/translation/test_prompt_builder.py`

**Interfaces:**
- Consumes: `GlossaryTerm`, `_build_glossary_section()` (already private in `prompt_builder.py`, reused directly since same module).
- Produces: `build_reviewer_system_prompt(target_language_name: str) -> str`; `build_terminology_validator_system_prompt(target_language_name: str, glossary_terms: list[GlossaryTerm] | None = None) -> str`. Task 3 calls both.

- [x] **Step 1: Write the failing tests — append to `tests/translation/test_prompt_builder.py`**

```python
from app.translation.prompt_builder import (
    build_reviewer_system_prompt,
    build_terminology_validator_system_prompt,
)


def test_reviewer_prompt_mentions_target_language():
    prompt = build_reviewer_system_prompt("European Spanish")

    assert "European Spanish" in prompt


def test_reviewer_prompt_lists_semantic_drift_categories():
    prompt = build_reviewer_system_prompt("European Spanish")

    assert "added" in prompt
    assert "removed" in prompt
    assert "degree of certainty" in prompt
    assert "terminology" in prompt


def test_reviewer_prompt_specifies_response_shape():
    prompt = build_reviewer_system_prompt("European Spanish")

    assert '"passed"' in prompt
    assert '"issues"' in prompt


def test_terminology_validator_prompt_mentions_target_language():
    prompt = build_terminology_validator_system_prompt("European Spanish")

    assert "European Spanish" in prompt


def test_terminology_validator_prompt_specifies_response_shape():
    prompt = build_terminology_validator_system_prompt("European Spanish")

    assert '"compliant"' in prompt
    assert '"violations"' in prompt


def test_terminology_validator_prompt_includes_glossary_when_given():
    terms = [GlossaryTerm(source="rover", target="rover")]

    prompt = build_terminology_validator_system_prompt("European Spanish", terms)

    assert "MANDATORY GLOSSARY" in prompt
    assert "rover -> rover" in prompt


def test_terminology_validator_prompt_has_no_glossary_section_when_no_terms_given():
    prompt = build_terminology_validator_system_prompt("European Spanish")

    assert "MANDATORY GLOSSARY" not in prompt
```

- [x] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest tests/translation/test_prompt_builder.py -v`
Expected: FAIL with `ImportError: cannot import name 'build_reviewer_system_prompt'`.

- [x] **Step 3: Add the new prompt builders to `app/translation/prompt_builder.py`**

Append after `build_system_prompt`:

```python
_REVIEWER_INSTRUCTIONS_TEMPLATE = """You are a senior technical reviewer for GNSS, RTK, PPK, surveying and geodesy content translated from English to {target_language_name}.

Compare the SOURCE text and its TRANSLATION, provided in the user message. Check specifically for:
1. Information added that was not in the source.
2. Information removed that was in the source.
3. Information altered (numbers, units, technical claims).
4. Changes to conditional statements or qualifications.
5. Changes to the degree of certainty expressed.
6. Changes to warnings or limitations.
7. Incorrect or inconsistent terminology.

If any of these problems are present, the review fails."""

_REVIEWER_RESPONSE_FORMAT_RULE = """Respond ONLY with a JSON object matching this exact shape:
{"passed": true, "issues": [{"type": "...", "description": "..."}]}
If no problems are found, return "passed": true and an empty "issues" list."""

_TERMINOLOGY_VALIDATOR_INSTRUCTIONS_TEMPLATE = """You are a terminology auditor for GNSS, RTK, PPK, surveying and geodesy technical translations into {target_language_name}.

Given the TRANSLATION in the user message, verify that every mandatory glossary term used conceptually in the text uses EXACTLY the mandated target term. Flag any deviation."""

_TERMINOLOGY_VALIDATOR_RESPONSE_FORMAT_RULE = """Respond ONLY with a JSON object matching this exact shape:
{"compliant": true, "violations": [{"term": "...", "expected": "...", "found_as": "...", "note": "..."}]}
If the translation fully complies, return "compliant": true and an empty "violations" list."""


def build_reviewer_system_prompt(target_language_name: str) -> str:
    sections = [
        _REVIEWER_INSTRUCTIONS_TEMPLATE.format(target_language_name=target_language_name),
        _REVIEWER_RESPONSE_FORMAT_RULE,
    ]
    return "\n\n".join(sections)


def build_terminology_validator_system_prompt(
    target_language_name: str,
    glossary_terms: list[GlossaryTerm] | None = None,
) -> str:
    sections = [
        _TERMINOLOGY_VALIDATOR_INSTRUCTIONS_TEMPLATE.format(
            target_language_name=target_language_name
        ),
    ]

    if glossary_terms:
        sections.append(_build_glossary_section(glossary_terms))

    sections.append(_TERMINOLOGY_VALIDATOR_RESPONSE_FORMAT_RULE)

    return "\n\n".join(sections)
```

- [x] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/translation/test_prompt_builder.py -v`
Expected: 12 passed (5 existing + 7 new).

- [x] **Step 5: Commit**

```bash
git add app/translation/prompt_builder.py tests/translation/test_prompt_builder.py
git commit -m "feat: add reviewer and terminology validator system prompts"
```

---

### Task 3: `DeepSeekClient.review()` and `.validate_terminology()`

**Files:**
- Modify: `app/translation/deepseek_client.py`
- Modify: `tests/translation/test_deepseek_client.py`

**Interfaces:**
- Consumes: `build_reviewer_system_prompt`, `build_terminology_validator_system_prompt` (Task 2); `ReviewResult`, `TerminologyValidationResult` (Task 1).
- Produces: `DeepSeekClient.__init__(..., qa_model: str = "deepseek-v4-pro", ...)`; `.review(source_text: str, translated_text: str, target_language_name: str) -> ReviewResult`; `.validate_terminology(translated_text: str, target_language_name: str, glossary_terms: list[GlossaryTerm] | None = None) -> TerminologyValidationResult`.

- [x] **Step 1: Write the failing tests — append to `tests/translation/test_deepseek_client.py`**

```python
from app.translation.schemas import ReviewResult, TerminologyValidationResult


def test_review_returns_parsed_review_result():
    fake_client = _fake_openai_client({"passed": True, "issues": []})

    client = DeepSeekClient(api_key="test-key", client=fake_client)
    result = client.review(
        source_text="1 cm accuracy",
        translated_text="1 cm de precisión",
        target_language_name="European Spanish",
    )

    assert isinstance(result, ReviewResult)
    assert result.passed is True


def test_review_calls_api_with_qa_model_and_both_texts_in_user_message():
    fake_client = _fake_openai_client({"passed": False, "issues": []})

    client = DeepSeekClient(api_key="test-key", qa_model="deepseek-v4-pro", client=fake_client)
    client.review(
        source_text="1 cm accuracy",
        translated_text="2 cm de precisión",
        target_language_name="European Spanish",
    )

    _, kwargs = fake_client.chat.completions.create.call_args
    assert kwargs["model"] == "deepseek-v4-pro"
    assert kwargs["response_format"] == {"type": "json_object"}
    user_message = kwargs["messages"][1]["content"]
    assert "1 cm accuracy" in user_message
    assert "2 cm de precisión" in user_message


def test_validate_terminology_returns_parsed_result():
    fake_client = _fake_openai_client({"compliant": True, "violations": []})

    client = DeepSeekClient(api_key="test-key", client=fake_client)
    result = client.validate_terminology(
        translated_text="estación base",
        target_language_name="European Spanish",
    )

    assert isinstance(result, TerminologyValidationResult)
    assert result.compliant is True


def test_validate_terminology_passes_glossary_into_system_prompt():
    fake_client = _fake_openai_client({"compliant": True, "violations": []})
    terms = [GlossaryTerm(source="rover", target="rover")]

    client = DeepSeekClient(api_key="test-key", client=fake_client)
    client.validate_terminology(
        translated_text="rover",
        target_language_name="European Spanish",
        glossary_terms=terms,
    )

    _, kwargs = fake_client.chat.completions.create.call_args
    system_message = kwargs["messages"][0]["content"]
    assert "rover -> rover" in system_message


def test_translate_and_review_use_independent_calls_with_separate_models():
    fake_client = _fake_openai_client({"translation": "x", "confidence": 0.9})

    client = DeepSeekClient(
        api_key="test-key", model="deepseek-v4-pro", qa_model="deepseek-v4-flash", client=fake_client
    )
    client.translate("hello", target_language_name="European Spanish")

    _, kwargs = fake_client.chat.completions.create.call_args
    assert kwargs["model"] == "deepseek-v4-pro"

    fake_client.chat.completions.create.return_value.choices[0].message.content = json.dumps(
        {"passed": True, "issues": []}
    )
    client.review("hello", "hola", target_language_name="European Spanish")

    _, kwargs = fake_client.chat.completions.create.call_args
    assert kwargs["model"] == "deepseek-v4-flash"
```

- [x] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest tests/translation/test_deepseek_client.py -v`
Expected: FAIL with `AttributeError: 'DeepSeekClient' object has no attribute 'review'` (or `TypeError` on `qa_model` kwarg).

- [x] **Step 3: Modify `app/translation/deepseek_client.py`**

Replace the full file contents with:

```python
"""Client for calling DeepSeek's OpenAI-compatible chat completions API
to translate and quality-check technical GNSS/RTK content.

DeepSeek's API is OpenAI-compatible (base_url swap only) and supports
JSON mode for structured output — see BIBLIOGRAFIA.md section 8.

Per the project brief (section 9), translation, technical review and
terminology validation are three independent calls, never combined into
a single request.
"""
from __future__ import annotations

import json

from openai import OpenAI

from app.translation.prompt_builder import (
    GlossaryTerm,
    build_reviewer_system_prompt,
    build_system_prompt,
    build_terminology_validator_system_prompt,
)
from app.translation.schemas import (
    ReviewResult,
    TerminologyValidationResult,
    TranslationResult,
)


class DeepSeekClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com",
        model: str = "deepseek-v4-pro",
        qa_model: str = "deepseek-v4-pro",
        client: OpenAI | None = None,
    ) -> None:
        self._model = model
        self._qa_model = qa_model
        self._client = client or OpenAI(api_key=api_key, base_url=base_url)

    def translate(
        self,
        source_text: str,
        target_language_name: str,
        context: str = "",
        glossary_terms: list[GlossaryTerm] | None = None,
    ) -> TranslationResult:
        system_prompt = build_system_prompt(target_language_name, glossary_terms)
        user_prompt = self._build_translate_user_prompt(source_text, context)

        data = self._call(self._model, system_prompt, user_prompt)
        return TranslationResult.model_validate(data)

    def review(
        self,
        source_text: str,
        translated_text: str,
        target_language_name: str,
    ) -> ReviewResult:
        system_prompt = build_reviewer_system_prompt(target_language_name)
        user_prompt = (
            f"SOURCE:\n{source_text}\n\nTRANSLATION:\n{translated_text}"
        )

        data = self._call(self._qa_model, system_prompt, user_prompt)
        return ReviewResult.model_validate(data)

    def validate_terminology(
        self,
        translated_text: str,
        target_language_name: str,
        glossary_terms: list[GlossaryTerm] | None = None,
    ) -> TerminologyValidationResult:
        system_prompt = build_terminology_validator_system_prompt(
            target_language_name, glossary_terms
        )
        user_prompt = f"TRANSLATION:\n{translated_text}"

        data = self._call(self._qa_model, system_prompt, user_prompt)
        return TerminologyValidationResult.model_validate(data)

    def _call(self, model: str, system_prompt: str, user_prompt: str) -> dict:
        response = self._client.chat.completions.create(
            model=model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        raw_content = response.choices[0].message.content
        return json.loads(raw_content)

    @staticmethod
    def _build_translate_user_prompt(source_text: str, context: str) -> str:
        if context:
            return f"Context: {context}\n\nText to translate:\n{source_text}"
        return f"Text to translate:\n{source_text}"
```

- [x] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/translation/test_deepseek_client.py -v`
Expected: 10 passed (5 existing + 5 new).

- [x] **Step 5: Run the full test suite**

Run: `.venv/Scripts/python.exe -m pytest -v`
Expected: all tests pass (21 existing - 0 removed + 6 schema + 7 prompt + 5 client = 39 total... exact count confirmed at execution time).

- [x] **Step 6: Commit**

```bash
git add app/translation/deepseek_client.py tests/translation/test_deepseek_client.py
git commit -m "feat: add DeepSeekClient.review() and .validate_terminology()"
```

---

### Task 4: Update tracking docs

**Files:**
- Modify: `PLA-ACCIO.md`
- Modify: `LOG.md`

- [x] **Step 1:** Mark `PLA-ACCIO.md` FASE 4.4 as done, note the model-per-call design (`model` vs `qa_model`).
- [x] **Step 2:** Add a `LOG.md` entry summarizing this session.
- [x] **Step 3: Commit**

```bash
git add PLA-ACCIO.md LOG.md docs/superpowers/plans/2026-07-23-deepseek-reviewer-terminology-validator.md
git commit -m "docs: mark FASE 4.4 done, log reviewer/terminology validator session"
```

---

## Out of scope for this plan

- QA scoring system (5 dimensions, thresholds — brief section 13) — FASE 7, needs numerical/units/URL checkers first.
- Glossary loading from `glossary/*.json` and `get_relevant_terms()` filtering — FASE 5, still uses manually-constructed `GlossaryTerm` lists for now.
- Wiring `translate()` + `review()` + `validate_terminology()` into one orchestrated pipeline — that belongs to FASE 8 (WPML integration / `translate.py` CLI), after WordPress access exists.
