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
