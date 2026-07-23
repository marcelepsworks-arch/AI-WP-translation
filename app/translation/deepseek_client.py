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
