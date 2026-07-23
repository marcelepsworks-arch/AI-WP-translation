"""Splits long source text into chunks that fit a character budget,
preserving paragraph and sentence boundaries so technical content
(numbers, units, terminology) is never cut mid-word.
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.translation.deepseek_client import DeepSeekClient
    from app.translation.prompt_builder import GlossaryTerm


def chunk_text(text: str, max_chars: int = 4000) -> list[str]:
    paragraphs = [p for p in text.split("\n\n") if p.strip()]

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for paragraph in paragraphs:
        if len(paragraph) > max_chars:
            if current:
                chunks.append("\n\n".join(current))
                current, current_len = [], 0
            chunks.extend(_split_by_sentences(paragraph, max_chars))
            continue

        added_len = len(paragraph) + (2 if current else 0)
        if current and current_len + added_len > max_chars:
            chunks.append("\n\n".join(current))
            current, current_len = [paragraph], len(paragraph)
        else:
            current.append(paragraph)
            current_len += added_len

    if current:
        chunks.append("\n\n".join(current))

    return chunks


def _split_by_sentences(paragraph: str, max_chars: int) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", paragraph)

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for sentence in sentences:
        added_len = len(sentence) + (1 if current else 0)
        if current and current_len + added_len > max_chars:
            chunks.append(" ".join(current))
            current, current_len = [sentence], len(sentence)
        else:
            current.append(sentence)
            current_len += added_len

    if current:
        chunks.append(" ".join(current))

    return chunks


def translate_long_text(
    client: "DeepSeekClient",
    text: str,
    target_language_name: str,
    context: str = "",
    glossary_terms: "list[GlossaryTerm] | None" = None,
    max_chars: int = 4000,
) -> str:
    chunks = chunk_text(text, max_chars)
    translated_chunks = [
        client.translate(
            chunk,
            target_language_name=target_language_name,
            context=context,
            glossary_terms=glossary_terms,
        ).translation
        for chunk in chunks
    ]
    return "\n\n".join(translated_chunks)
