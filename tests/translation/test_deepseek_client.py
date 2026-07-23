import json
from unittest.mock import MagicMock

from app.translation.deepseek_client import DeepSeekClient
from app.translation.prompt_builder import GlossaryTerm
from app.translation.schemas import (
    ReviewResult,
    TerminologyValidationResult,
    TranslationResult,
)


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
