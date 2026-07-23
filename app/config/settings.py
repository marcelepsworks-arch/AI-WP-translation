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
