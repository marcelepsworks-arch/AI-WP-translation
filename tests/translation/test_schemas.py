import pytest
from pydantic import ValidationError

from app.translation.schemas import (
    ReviewResult,
    TerminologyValidationResult,
    TerminologyViolation,
    TranslationIssue,
    TranslationResult,
)


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
