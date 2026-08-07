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
import threading
import time

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
        # model -> {"input": tokens, "output": tokens}. Cumulative across every
        # translate()/review()/validate_terminology() call on this client.
        # Guarded by a lock since translate_blocks() can run concurrently
        # (max_workers > 1) across multiple threads sharing one client.
        self.usage: dict[str, dict[str, int]] = {}
        self._usage_lock = threading.Lock()

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
        user_prompt = f"SOURCE:\n{source_text}\n\nTRANSLATION:\n{translated_text}"

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

    _MAX_RETRIES = 2

    def _call(self, model: str, system_prompt: str, user_prompt: str) -> dict:
        last_error: Exception = RuntimeError("unreachable")
        for attempt in range(self._MAX_RETRIES + 1):
            response = self._client.chat.completions.create(
                model=model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            raw_content = response.choices[0].message.content
            if raw_content:
                try:
                    data = json.loads(raw_content)
                except json.JSONDecodeError as exc:
                    last_error = exc
                else:
                    self._record_usage(model, response)
                    return data
            else:
                last_error = ValueError("DeepSeek returned an empty response")

            if attempt < self._MAX_RETRIES:
                time.sleep(1)

        raise RuntimeError(
            f"DeepSeek returned no usable content after {self._MAX_RETRIES + 1} attempts"
        ) from last_error

    def _record_usage(self, model: str, response) -> None:
        # Best-effort: token accounting must never break a translation. Also
        # silently no-ops against mocked responses in tests (MagicMock
        # attributes fail the int() conversion and are caught here).
        try:
            usage = response.usage
            prompt_tokens = int(usage.prompt_tokens)
            completion_tokens = int(usage.completion_tokens)
        except (AttributeError, TypeError, ValueError):
            return

        with self._usage_lock:
            bucket = self.usage.setdefault(model, {"input": 0, "output": 0})
            bucket["input"] += prompt_tokens
            bucket["output"] += completion_tokens

    @staticmethod
    def _build_translate_user_prompt(source_text: str, context: str) -> str:
        if context:
            return f"Context: {context}\n\nText to translate:\n{source_text}"
        return f"Text to translate:\n{source_text}"
