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
