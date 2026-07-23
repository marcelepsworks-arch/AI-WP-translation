"""One-off empirical analysis: estimate DeepSeek translation cost for real
precision-gnss.com pages scraped into .firecrawl/*.md.

Not part of the production pipeline — a throwaway script used to produce
the cost figures in the executive summary report. Uses the real system
prompts from app/translation/prompt_builder.py and the real chunk_text()
splitter, so the numbers reflect actual code behavior, not guesses.

Token estimate: ~4 characters per token (standard rule-of-thumb for
English/Spanish text with GPT/DeepSeek-style BPE tokenizers).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.translation.chunking import chunk_text
from app.translation.prompt_builder import (
    GlossaryTerm,
    build_reviewer_system_prompt,
    build_system_prompt,
    build_terminology_validator_system_prompt,
)

CHARS_PER_TOKEN = 4.0

# DeepSeek pricing, per 1M tokens, USD (api-docs.deepseek.com/quick_start/pricing/, 2026-07-23)
PRICING = {
    "deepseek-v4-pro": {"input_cache_miss": 0.435, "output": 0.87},
    "deepseek-v4-flash": {"input_cache_miss": 0.14, "output": 0.28},
}

SAMPLE_GLOSSARY = [
    GlossaryTerm(source="base station", target="estación base", notes="GNSS/RTK context"),
    GlossaryTerm(source="rover", target="rover"),
    GlossaryTerm(source="fix", target="solución fija"),
]

TRANSLATOR_SYSTEM = build_system_prompt("European Spanish", SAMPLE_GLOSSARY)
REVIEWER_SYSTEM = build_reviewer_system_prompt("European Spanish")
VALIDATOR_SYSTEM = build_terminology_validator_system_prompt("European Spanish", SAMPLE_GLOSSARY)


def clean_prose(markdown_text: str) -> str:
    """Strip markdown link/image syntax and raw URLs to approximate the
    'translatable prose only' text an extractor would actually send —
    mirrors the brief's protected-content rules (section 7.2)."""
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", markdown_text)  # images
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)  # links -> keep label text
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[#_*`>-]{1,3}", "", text)  # markdown punctuation
    text = re.sub(r"\n{2,}", "\n\n", text)
    return text.strip()


def tokens(char_count: float) -> float:
    return char_count / CHARS_PER_TOKEN


def cost(model: str, input_tokens: float, output_tokens: float) -> float:
    rates = PRICING[model]
    return (input_tokens * rates["input_cache_miss"] + output_tokens * rates["output"]) / 1_000_000


def estimate_page(path: Path) -> None:
    raw = path.read_text(encoding="utf-8")
    prose = clean_prose(raw)

    chunks = chunk_text(prose, max_chars=4000)
    n_chunks = len(chunks)

    # Per-chunk output size assumption: translated text is roughly the same
    # length as source (Spanish tends to run ~10-15% longer than English),
    # plus ~150 chars of JSON wrapper overhead.
    total_translate_input_chars = sum(len(TRANSLATOR_SYSTEM) + len(c) + 50 for c in chunks)
    total_translate_output_chars = sum(len(c) * 1.15 + 150 for c in chunks)

    total_review_input_chars = sum(len(REVIEWER_SYSTEM) + len(c) + len(c) * 1.15 + 60 for c in chunks)
    total_review_output_chars = n_chunks * 120  # small JSON, mostly "passed": true

    total_validate_input_chars = sum(len(VALIDATOR_SYSTEM) + len(c) * 1.15 + 40 for c in chunks)
    total_validate_output_chars = n_chunks * 100

    translate_in_tok = tokens(total_translate_input_chars)
    translate_out_tok = tokens(total_translate_output_chars)
    review_in_tok = tokens(total_review_input_chars)
    review_out_tok = tokens(total_review_output_chars)
    validate_in_tok = tokens(total_validate_input_chars)
    validate_out_tok = tokens(total_validate_output_chars)

    translate_only_pro = cost("deepseek-v4-pro", translate_in_tok, translate_out_tok)
    full_pro = translate_only_pro + cost("deepseek-v4-pro", review_in_tok, review_out_tok) + cost(
        "deepseek-v4-pro", validate_in_tok, validate_out_tok
    )
    full_mixed = translate_only_pro + cost("deepseek-v4-flash", review_in_tok, review_out_tok) + cost(
        "deepseek-v4-flash", validate_in_tok, validate_out_tok
    )

    word_count = len(prose.split())
    print(f"=== {path.name} ===")
    print(f"  raw markdown chars:      {len(raw):>7,}")
    print(f"  cleaned prose chars:     {len(prose):>7,}")
    print(f"  cleaned prose words:     {word_count:>7,}")
    print(f"  chunks (max 4000 chars): {n_chunks:>7}")
    print(f"  cost - translate only (v4-pro):        ${translate_only_pro:.5f}")
    print(f"  cost - full pipeline (v4-pro only):     ${full_pro:.5f}")
    print(f"  cost - full pipeline (pro+flash QA):    ${full_mixed:.5f}")
    print(f"  cost per 1,000 chars (full pro pipeline): ${(full_pro / len(prose) * 1000):.5f}")
    print()


if __name__ == "__main__":
    firecrawl_dir = Path(__file__).resolve().parent.parent / ".firecrawl"
    for md_file in sorted(firecrawl_dir.glob("*.md")):
        estimate_page(md_file)
