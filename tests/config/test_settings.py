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
