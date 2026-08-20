"""Identity of the translation configuration that produced a translation.

A remembered translation is only reusable while the thing that produced it
is unchanged. Rather than a hand-maintained PROMPT_VERSION constant --
which works exactly until the first person edits a prompt and forgets to
bump it -- this hashes the actual prompt text, the actual glossary, and
the model names. Editing any of them invalidates the memory
automatically, and nothing can silently serve translations from a
previous generation.

The per-block glossary subset (`get_relevant_terms`) is deliberately not
part of the hash: it is a pure function of the source text and the full
glossary, and the source text is already part of the memory key.
"""
from __future__ import annotations

import hashlib
import json

from app.translation.glossary import GlossaryEntry
from app.translation.prompt_builder import build_reviewer_system_prompt, build_system_prompt


def memory_fingerprint(
    target_language_name: str,
    glossary_entries: list[GlossaryEntry],
    model: str,
    qa_model: str,
) -> str:
    """Includes the reviewer prompt as well as the translator's: a memory
    hit inherits the original run's `review_passed`, so a changed reviewer
    must invalidate it too.
    """
    payload = json.dumps(
        {
            "translator_prompt": build_system_prompt(target_language_name, None),
            "reviewer_prompt": build_reviewer_system_prompt(target_language_name),
            "glossary": sorted(
                (entry.source, entry.target, entry.language, entry.status) for entry in glossary_entries
            ),
            "model": model,
            "qa_model": qa_model,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
