"""Decides whether a page/post needs a brand-new translation, an update
to an existing one, or nothing at all -- and if it's an update, translates
only the blocks whose source text actually changed.

Three outcomes, driven by `gnss-bridge`'s `/translation-status` (now
including WPML's own `needs_update` flag, ROADMAP.md FASE 6):

- No translation exists yet -> full translation via `translate_page()`
  (unchanged behaviour, same as running `app.cli.translate` directly).
- A translation exists and WPML says it's up to date -> nothing to do,
  zero DeepSeek calls.
- A translation exists and WPML says the source changed -> re-extract the
  source, compare each block's hash against `_gnss_block_hashes` (saved on
  the translated post at write time), translate only the blocks that
  actually changed, reuse the rest, and update the existing translated
  post in place (never creates a duplicate).

Usage:
    python -m app.cli.sync --post-id 6273 --post-type page --language es
"""
from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path

from pydantic import BaseModel

from app.cli.progress_html import ProgressTracker
from app.cli.translate import (
    BlockResult,
    build_translation_payload,
    configure_logging,
    hash_source,
    overall_decision,
    translate_blocks,
    translate_page,
)
from app.config.settings import load_settings
from app.extraction.content_extractor import extract_page_content
from app.extraction.elementor_extractor import parse_elementor_document
from app.translation.deepseek_client import DeepSeekClient
from app.translation.glossary import GlossaryEntry, load_glossary_files
from app.translation.pricing import estimate_cost_usd
from app.wordpress import content as wp_content
from app.wordpress import wpml as wp_wpml
from app.wordpress.client import WordPressClient

logger = logging.getLogger(__name__)

_GLOSSARY_FILES = [Path("glossary/gnss.json"), Path("glossary/surveying.json")]


def _build_wp_client() -> WordPressClient:
    base_url = os.environ.get("WP_URL") or os.environ["STAGING_URL"]
    basic_auth = None
    if os.environ.get("STAGING_BASIC_AUTH_USER"):
        basic_auth = (os.environ["STAGING_BASIC_AUTH_USER"], os.environ["STAGING_BASIC_AUTH_PASSWORD"])
    return WordPressClient(
        base_url=base_url,
        basic_auth=basic_auth,
        wp_username=os.environ.get("WP_USERNAME"),
        wp_app_password=os.environ.get("WP_APPLICATION_PASSWORD"),
    )


class SyncResult(BaseModel):
    post_id: int
    post_type: str
    target_language: str
    outcome: str  # "created" | "updated" | "up_to_date"
    translated_post_id: int | None = None
    blocks_translated: int = 0
    blocks_reused: int = 0
    overall_decision: str | None = None


def update_page(
    wp_client: WordPressClient,
    deepseek: DeepSeekClient,
    glossary_entries: list[GlossaryEntry],
    post_id: int,
    translated_post_id: int,
    post_type: str = "page",
    target_language: str = "es",
    max_workers: int = 1,
    progress_html_path: Path | None = None,
) -> SyncResult:
    """Re-translates only the blocks whose source text changed since the
    last translation, and updates the existing translated post in place.
    """
    logger.info(
        "syncing %s %d -> %s: re-extracting source to diff against translated %s %d",
        post_type, post_id, target_language, post_type, translated_post_id,
    )
    get_fn = wp_content.get_page if post_type == "page" else wp_content.get_post
    page = get_fn(wp_client, post_id)
    translated_page = get_fn(wp_client, translated_post_id)

    old_hashes: dict[str, dict] = json.loads(
        translated_page.get("meta", {}).get("_gnss_block_hashes") or "{}"
    )

    elementor_doc = parse_elementor_document(page.get("meta", {}).get("_elementor_data", ""))
    elementor_blocks = elementor_doc.blocks if elementor_doc is not None else []
    blocks = extract_page_content(page, skip_body=elementor_doc is not None)
    all_blocks = blocks + elementor_blocks

    changed_blocks = []
    reused_results: list[BlockResult] = []
    for block in all_blocks:
        old = old_hashes.get(block.content_id)
        if old is not None and old.get("hash") == hash_source(block.source):
            reused_results.append(
                BlockResult(
                    content_id=block.content_id, type=block.type, source=block.source, translation=old["translation"]
                )
            )
        else:
            changed_blocks.append(block)

    logger.info(
        "%s %d: %d block(s) changed, %d reused unchanged",
        post_type, post_id, len(changed_blocks), len(reused_results),
    )

    progress = (
        ProgressTracker(len(changed_blocks), post_id, target_language, progress_html_path)
        if progress_html_path
        else None
    )
    new_results = (
        translate_blocks(deepseek, changed_blocks, target_language, glossary_entries, max_workers=max_workers, progress=progress)
        if changed_blocks
        else []
    )
    if deepseek.usage:
        logger.info(
            "token usage for %s %d update: %s (estimated cost: $%.4f)",
            post_type, post_id, deepseek.usage, estimate_cost_usd(deepseek.usage),
        )

    results = new_results + reused_results
    results_by_id = {r.content_id: r for r in results}
    decision = overall_decision(new_results) if new_results else "auto_approve"

    payload = build_translation_payload(page, post_id, post_type, blocks, all_blocks, elementor_doc, results, results_by_id)

    endpoint = f"/wp-json/wp/v2/{'pages' if post_type == 'page' else 'posts'}/{translated_post_id}"
    wp_client.post(endpoint, json=payload)
    logger.info("updated draft %s %d (%s translation of %s %d)", post_type, translated_post_id, target_language, post_type, post_id)

    if progress is not None:
        progress.finish(decision)

    return SyncResult(
        post_id=post_id,
        post_type=post_type,
        target_language=target_language,
        outcome="updated",
        translated_post_id=translated_post_id,
        blocks_translated=len(new_results),
        blocks_reused=len(reused_results),
        overall_decision=decision,
    )


def sync_page(
    wp_client: WordPressClient,
    deepseek: DeepSeekClient,
    glossary_entries: list[GlossaryEntry],
    post_id: int,
    post_type: str = "page",
    target_language: str = "es",
    max_workers: int = 1,
    progress_html_path: Path | None = None,
) -> SyncResult:
    status = wp_wpml.get_translation_status(wp_client, post_id, target_language)

    if not status.get("translation_exists"):
        logger.info("%s %d has no %s translation yet -- creating one from scratch", post_type, post_id, target_language)
        result = translate_page(
            wp_client, deepseek, glossary_entries, post_id, post_type, target_language,
            dry_run=False, max_workers=max_workers, progress_html_path=progress_html_path,
        )
        return SyncResult(
            post_id=post_id, post_type=post_type, target_language=target_language, outcome="created",
            translated_post_id=result.translated_post_id, blocks_translated=len(result.blocks),
            overall_decision=result.overall_decision,
        )

    translated_post_id = status["translated_post_id"]

    if status.get("needs_update") is False:
        logger.info(
            "%s %d's %s translation (%d) is already up to date -- nothing to do",
            post_type, post_id, target_language, translated_post_id,
        )
        return SyncResult(
            post_id=post_id, post_type=post_type, target_language=target_language, outcome="up_to_date",
            translated_post_id=translated_post_id,
        )

    # needs_update is True, or None/unknown (older gnss-bridge, or WPML
    # status unavailable) -- in the unknown case we still only re-translate
    # blocks whose hash actually differs, so an unnecessary check costs
    # nothing beyond the extraction/diff itself.
    return update_page(
        wp_client, deepseek, glossary_entries, post_id, translated_post_id, post_type, target_language,
        max_workers=max_workers, progress_html_path=progress_html_path,
    )


def main() -> None:
    from dotenv import load_dotenv

    load_dotenv()
    configure_logging()

    parser = argparse.ArgumentParser(
        description="Create or update a page/post's translation, re-translating only what changed."
    )
    parser.add_argument("--post-id", type=int, required=True)
    parser.add_argument("--post-type", choices=["page", "post"], default="page")
    parser.add_argument("--language", default="es")
    parser.add_argument(
        "--workers", type=int, default=5, help="Concurrent DeepSeek calls across blocks (default 5, 1=sequential)"
    )
    parser.add_argument("--no-progress-html", action="store_true")
    args = parser.parse_args()

    settings = load_settings()
    wp_client = _build_wp_client()
    deepseek = DeepSeekClient(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        model=settings.default_model,
        qa_model=settings.qa_model,
    )
    glossary_entries = load_glossary_files(_GLOSSARY_FILES)
    progress_html_path = None if args.no_progress_html else Path("logs/progress.html")

    result = sync_page(
        wp_client, deepseek, glossary_entries, args.post_id, args.post_type, args.language,
        max_workers=args.workers, progress_html_path=progress_html_path,
    )

    print(f"Post {result.post_id} ({result.post_type}) -> {result.target_language}: {result.outcome}")
    if result.outcome == "created":
        print(f"Created draft {result.translated_post_id} ({result.blocks_translated} blocks translated)")
    elif result.outcome == "updated":
        print(
            f"Updated draft {result.translated_post_id}: {result.blocks_translated} block(s) re-translated, "
            f"{result.blocks_reused} reused unchanged"
        )
    else:
        print(f"Translation {result.translated_post_id} is already up to date -- nothing translated.")


if __name__ == "__main__":
    main()
