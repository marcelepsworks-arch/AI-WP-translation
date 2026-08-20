"""Environment-based configuration loading for the translation engine."""
from __future__ import annotations

import os
from dataclasses import dataclass, field


_AUTO_PUBLISH_MODES = {"off", "qa_gated", "all"}


@dataclass(frozen=True)
class Settings:
    deepseek_api_key: str
    deepseek_base_url: str = "https://api.deepseek.com"
    default_model: str = "deepseek-v4-pro"
    qa_model: str = "deepseek-v4-pro"
    source_language: str = "en"
    target_languages: list[str] = field(default_factory=lambda: ["es"])
    # "off" (default): every translation is always written as a draft,
    # pending human review -- the project's core safety guarantee.
    # "qa_gated": pages the QA layer scored auto_approve are published
    # immediately; anything flagged human_review/reject still becomes a
    # draft. "all": every translation is published immediately regardless
    # of QA decision. Deliberately opt-in and explicit in .env (never a
    # CLI flag someone could pass once by habit) -- see README "Autonomous
    # publishing" for the tradeoffs before turning this on.
    auto_publish_mode: str = "off"
    # Cross-page translation memory (app/storage/translation_memory.py).
    # On by default: it only ever reuses a translation that scored
    # auto_approve under an identical configuration fingerprint, and every
    # hit is re-checked before use. Set TRANSLATION_MEMORY=off to force
    # every block through the model again.
    translation_memory_enabled: bool = True
    translation_memory_path: str = "logs/translation_memory.sqlite3"


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

    auto_publish_mode = source.get("AUTO_PUBLISH_MODE", "off").strip().lower() or "off"
    if auto_publish_mode not in _AUTO_PUBLISH_MODES:
        raise ValueError(
            f"AUTO_PUBLISH_MODE must be one of {sorted(_AUTO_PUBLISH_MODES)}, got {auto_publish_mode!r}"
        )

    return Settings(
        deepseek_api_key=api_key,
        deepseek_base_url=source.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        default_model=source.get("DEFAULT_MODEL", "deepseek-v4-pro"),
        qa_model=source.get("QA_MODEL", "deepseek-v4-pro"),
        source_language=source.get("SOURCE_LANGUAGE", "en"),
        target_languages=target_languages,
        auto_publish_mode=auto_publish_mode,
        translation_memory_enabled=source.get("TRANSLATION_MEMORY", "on").strip().lower() != "off",
        translation_memory_path=source.get("TRANSLATION_MEMORY_PATH", "logs/translation_memory.sqlite3"),
    )
