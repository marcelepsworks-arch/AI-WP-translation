"""End-to-end translation orchestrator (FASE 8, brief section 16):
Extract -> Glossary -> DeepSeek (Translator + Reviewer) -> QA -> Score ->
WordPress write -> WPML link. Operates on one page/post at a time.

AUTO_PUBLISH is intentionally not a runtime toggle: every translation this
orchestrator writes is always created as a `draft`. That is a hard product
guarantee repeated throughout the project docs (MEMORIA.md, ROADMAP.md
FASE 8.3), not something that should be one flipped env var away from being
violated.

Per-block QA does NOT gate whether the page gets written (changed
2026-08-06, MEMORIA.md): on a long page, some block being flagged is close
to certain — either a genuine issue (the Reviewer catching added/altered
meaning) or a mechanical-checker false positive, and blocking the entire
draft on any single flagged block meant real pages almost never got
written. The page is always written as a draft (never published either
way), and any non-auto_approve block is logged as needing human review
before publishing — see `PageTranslationResult.blocks` / `.overall_decision`
and the WARNING lines in logs/translate_audit.log.

Known limitation, documented rather than hidden: the translated body HTML is
reconstructed from the extracted ContentBlocks (heading/paragraph/list_item
only), which loses the original heading level and any inline formatting or
links. That is good enough to validate the pipeline end-to-end against a
simple page, but is not yet a faithful Elementor round-trip — that depends
on FASE 3.3 (elementor_extractor), still deferred (PLA-ACCIO.md).

Usage:
    python -m app.cli.translate --post-id 6273 --post-type page --dry-run
    python -m app.cli.translate --post-id 6273 --post-type page
    python -m app.cli.translate --post-id 4309 --post-type page --workers 5

Progress is printed live per block ("[i/N] block_id -> decision") since a
real page can have 100+ blocks and take several minutes; --workers > 1 runs
independent blocks concurrently (translate+review within one block stays
sequential). Every run is also logged to logs/translate_audit.log.

Reads WordPress connection details from .env: WP_URL (falls back to
STAGING_URL), STAGING_BASIC_AUTH_USER/PASSWORD (optional), WP_USERNAME,
WP_APPLICATION_PASSWORD (a real WordPress Application Password — see
BIBLIOGRAFIA.md section 5, not the account's login password).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from pydantic import BaseModel

from app.config.settings import load_settings
from app.cli.progress_html import ProgressTracker
from app.extraction.content_extractor import extract_page_content
from app.extraction.elementor_extractor import parse_elementor_document
from app.extraction.schemas import ContentBlock
from app.qa.html_sanitizer import sanitize_html
from app.qa.numerical_checker import check_numbers
from app.qa.scoring import QAReport, score_translation
from app.qa.terminology_checker import check_protected_terms
from app.qa.url_validator import check_urls
from app.translation.deepseek_client import DeepSeekClient
from app.translation.glossary import GlossaryEntry, get_relevant_terms, load_glossary_files
from app.translation.pricing import estimate_cost_usd
from app.wordpress import content as wp_content
from app.wordpress import wpml as wp_wpml
from app.wordpress.client import WordPressClient

logger = logging.getLogger(__name__)

LANGUAGE_NAMES = {"es": "European Spanish"}

_BODY_BLOCK_TYPES = {"heading", "paragraph", "list_item"}
_YOAST_FIELD_BY_BLOCK_TYPE = {
    "seo_title": "_yoast_wpseo_title",
    "seo_description": "_yoast_wpseo_metadesc",
}
_GLOSSARY_FILES = [Path("glossary/gnss.json"), Path("glossary/surveying.json")]


class BlockResult(BaseModel):
    content_id: str
    type: str
    source: str
    translation: str
    qa: QAReport | None = None


class PageTranslationResult(BaseModel):
    post_id: int
    post_type: str
    target_language: str
    blocks: list[BlockResult]
    overall_decision: str
    written: bool
    translated_post_id: int | None = None


class PageReview(BaseModel):
    """Everything `app.cli.publish` needs to write a reviewed translation to
    WordPress without re-calling DeepSeek: the exact WP payload built at
    translation time, plus the block-level results for reference.
    """

    post_id: int
    post_type: str
    target_language: str
    payload: dict
    blocks: list[BlockResult]


def hash_source(text: str) -> str:
    """Fingerprint of a block's source text, stored alongside its
    translation (`_gnss_block_hashes` meta) so a later run can tell which
    blocks changed since the last translation -- see `app.cli.sync`.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def build_block_hashes(blocks: list[ContentBlock], results_by_id: dict[str, BlockResult]) -> dict[str, dict]:
    return {
        block.content_id: {"hash": hash_source(block.source), "translation": results_by_id[block.content_id].translation}
        for block in blocks
        if block.content_id in results_by_id
    }


def _protected_terms(glossary_entries: list[GlossaryEntry], language: str) -> list[str]:
    return [entry.target for entry in glossary_entries if entry.language == language and entry.target == entry.source]


def translate_block(
    deepseek: DeepSeekClient,
    block: ContentBlock,
    target_language: str,
    target_language_name: str,
    glossary_entries: list[GlossaryEntry],
) -> BlockResult:
    if not block.translate or not block.source.strip():
        logger.info("block %s (%s): skipped (not translatable)", block.content_id, block.type)
        return BlockResult(
            content_id=block.content_id, type=block.type, source=block.source, translation=block.source
        )

    relevant_terms = get_relevant_terms(block.source, glossary_entries, language=target_language)
    translation_result = deepseek.translate(
        block.source, target_language_name, context=block.context, glossary_terms=relevant_terms
    )
    # Sanitized before anything downstream (QA checks, WordPress payloads)
    # ever sees it -- see app/qa/html_sanitizer.py for why.
    translation_result.translation = sanitize_html(translation_result.translation)
    review_result = deepseek.review(block.source, translation_result.translation, target_language_name)

    numeric = check_numbers(block.source, translation_result.translation)
    terminology = check_protected_terms(
        block.source, translation_result.translation, _protected_terms(glossary_entries, target_language)
    )
    url = check_urls(block.source, translation_result.translation)
    qa = score_translation(numeric, terminology, url, review_passed=review_result.passed)

    logger.info(
        "block %s (%s): %s score=%d confidence=%.2f",
        block.content_id, block.type, qa.decision, qa.score, translation_result.confidence,
    )
    if qa.decision != "auto_approve":
        logger.warning(
            "block %s (%s) flagged %s: numeric_passed=%s terminology_passed=%s url_passed=%s review_passed=%s"
            " | source=%r translation=%r review_issues=%s",
            block.content_id, block.type, qa.decision,
            qa.numeric_passed, qa.terminology_passed, qa.url_passed, qa.review_passed,
            block.source, translation_result.translation,
            [f"{i.type}: {i.description}" for i in review_result.issues],
        )

    return BlockResult(
        content_id=block.content_id,
        type=block.type,
        source=block.source,
        translation=translation_result.translation,
        qa=qa,
    )


def translate_blocks(
    deepseek: DeepSeekClient,
    blocks: list[ContentBlock],
    target_language: str,
    glossary_entries: list[GlossaryEntry],
    max_workers: int = 1,
    progress: ProgressTracker | None = None,
) -> list[BlockResult]:
    """Translates every block, printing live progress ("[i/N] id -> decision")
    since a real page can have 100+ blocks and take several minutes. When
    `progress` is given, also updates the local self-refreshing HTML view
    (app/cli/progress_html.py) after every block.

    Blocks are independent of each other (only the translate+review pair
    *within* one block is sequential), so max_workers > 1 runs them
    concurrently via a thread pool. Defaults to 1 (fully sequential) so
    existing callers/tests keep their exact call order and count.
    """
    target_language_name = LANGUAGE_NAMES.get(target_language, target_language)
    total = len(blocks)

    def _translate_one(indexed_block: tuple[int, ContentBlock]) -> tuple[int, BlockResult]:
        index, block = indexed_block
        print(f"[{index + 1}/{total}] translating {block.content_id} ({block.type})...", flush=True)
        result = translate_block(deepseek, block, target_language, target_language_name, glossary_entries)
        decision = result.qa.decision if result.qa else "skipped"
        print(f"[{index + 1}/{total}] {block.content_id} -> {decision}", flush=True)
        if progress is not None:
            progress.record(
                block.content_id, block.type, decision, result.qa.score if result.qa else None,
                usage=deepseek.usage, source=block.source, translation=result.translation,
            )
        return index, result

    if max_workers <= 1:
        return [_translate_one((index, block))[1] for index, block in enumerate(blocks)]

    results: list[BlockResult | None] = [None] * total
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for index, result in executor.map(_translate_one, enumerate(blocks)):
            results[index] = result
    return [result for result in results if result is not None]


def overall_decision(results: list[BlockResult]) -> str:
    decisions = [r.qa.decision for r in results if r.qa is not None]
    if not decisions:
        return "auto_approve"
    if "reject" in decisions:
        return "reject"
    if "human_review" in decisions:
        return "human_review"
    return "auto_approve"


def reassemble_body_html(blocks: list[ContentBlock], results_by_id: dict[str, BlockResult]) -> str:
    parts: list[str] = []
    for block in blocks:
        if block.type not in _BODY_BLOCK_TYPES:
            continue
        result = results_by_id.get(block.content_id)
        text = result.translation if result else block.source
        if not text.strip():
            continue
        tag = "h2" if block.type == "heading" else "p"
        parts.append(f"<{tag}>{text}</{tag}>")
    return "\n".join(parts)


def write_and_link_translation(
    wp_client: WordPressClient,
    endpoint: str,
    payload: dict,
    post_id: int,
    post_type: str,
    target_language: str,
) -> int:
    """POSTs the already-built payload as a new draft translation and links
    it to the source post's WPML trid. Shared by `translate_page` (immediate
    write) and `app.cli.publish` (write deferred until a human reviews the
    saved review artifact first).
    """
    translated_post_id = wp_client.post(endpoint, json=payload).json()["id"]
    logger.info(
        "created draft %s %d as %s translation of %s %d",
        post_type, translated_post_id, target_language, post_type, post_id,
    )

    status = wp_wpml.get_wpml_status(wp_client, post_id)
    trid = status.get("trid")
    if trid is not None:
        wp_wpml.link_translation(
            wp_client,
            element_id=translated_post_id,
            trid=int(trid),
            language_code=target_language,
            source_language_code=status.get("language_code") or "en",
        )
        logger.info("linked %s %d to trid %s as %s", post_type, translated_post_id, trid, target_language)
    else:
        logger.warning(
            "no trid found for %s %d — draft %d created but NOT linked in WPML, needs manual linking",
            post_type, post_id, translated_post_id,
        )
    return translated_post_id


def save_review(
    review_json_path: Path,
    post_id: int,
    post_type: str,
    target_language: str,
    payload: dict,
    results: list[BlockResult],
) -> None:
    """Saves everything `app.cli.publish` needs to write this translation to
    WordPress later, without calling DeepSeek again. The human review itself
    happens by reading the accompanying progress.html (source/translation
    side by side, QA decision per block) -- this file is just the "apply"
    data.
    """
    review_json_path.parent.mkdir(parents=True, exist_ok=True)
    review_json_path.write_text(
        PageReview(
            post_id=post_id, post_type=post_type, target_language=target_language, payload=payload, blocks=results
        ).model_dump_json(indent=2),
        encoding="utf-8",
    )


def build_translation_payload(
    page: dict,
    post_id: int,
    post_type: str,
    blocks: list[ContentBlock],
    all_blocks: list[ContentBlock],
    elementor_doc,
    results: list[BlockResult],
    results_by_id: dict[str, BlockResult],
) -> dict:
    """Builds the exact WordPress REST payload (title/content/meta/status)
    for a translated page, given the already-translated block results.
    Shared by `translate_page` (full create) and `app.cli.sync` (partial
    update, where some `results` are freshly translated and some are reused
    from the previous run via `_gnss_block_hashes`).
    """
    title_result = next((r for r in results if r.type == "title"), None)
    excerpt_result = next((r for r in results if r.type == "excerpt"), None)

    meta = {
        yoast_field: results_by_id[block.content_id].translation
        for block in blocks
        if (yoast_field := _YOAST_FIELD_BY_BLOCK_TYPE.get(block.type)) and block.content_id in results_by_id
    }

    if elementor_doc is not None:
        elementor_doc.apply_translations({r.content_id: r.translation for r in results})
        meta["_elementor_data"] = elementor_doc.to_json()
        original_meta = page.get("meta", {})
        for carry_over_field in ("_elementor_edit_mode", "_elementor_template_type", "_elementor_version"):
            if original_meta.get(carry_over_field):
                meta[carry_over_field] = original_meta[carry_over_field]
        logger.info("rebuilt _elementor_data for translated %s (source %s %d)", post_type, post_type, post_id)

    # Stored so a later `app.cli.sync` run can tell which blocks' source text
    # actually changed, and skip re-translating (and re-paying for) the rest.
    meta["_gnss_block_hashes"] = json.dumps(build_block_hashes(all_blocks, results_by_id))

    payload: dict = {
        "title": title_result.translation if title_result else page["title"]["rendered"],
        "content": reassemble_body_html(blocks, results_by_id),
        "status": "draft",  # never anything else -- see module docstring
        "meta": meta,
    }
    if excerpt_result:
        payload["excerpt"] = excerpt_result.translation
    return payload


def translate_page(
    wp_client: WordPressClient,
    deepseek: DeepSeekClient,
    glossary_entries: list[GlossaryEntry],
    post_id: int,
    post_type: str = "page",
    target_language: str = "es",
    dry_run: bool = True,
    max_workers: int = 1,
    progress_html_path: Path | None = None,
    review_json_path: Path | None = None,
) -> PageTranslationResult:
    logger.info("fetching %s %d for translation to %s", post_type, post_id, target_language)
    get_fn = wp_content.get_page if post_type == "page" else wp_content.get_post
    page = get_fn(wp_client, post_id)

    elementor_doc = parse_elementor_document(page.get("meta", {}).get("_elementor_data", ""))
    elementor_blocks = elementor_doc.blocks if elementor_doc is not None else []
    # When Elementor data is present, `content.rendered` is just Elementor's
    # own rendered mirror of the same text -- extracting both would translate
    # everything twice (double cost, and two independently-translated copies
    # that could disagree). skip_body=True keeps title/excerpt/SEO/taxonomy
    # blocks (not part of the Elementor tree) but drops the redundant body.
    blocks = extract_page_content(page, skip_body=elementor_doc is not None)
    if elementor_doc is not None:
        logger.info(
            "found _elementor_data for %s %d: %d translatable field(s) across the widget tree",
            post_type, post_id, len(elementor_blocks),
        )
    all_blocks = blocks + elementor_blocks

    logger.info("extracted %d blocks from %s %d", len(all_blocks), post_type, post_id)
    progress = (
        ProgressTracker(len(all_blocks), post_id, target_language, progress_html_path)
        if progress_html_path
        else None
    )
    results = translate_blocks(
        deepseek, all_blocks, target_language, glossary_entries, max_workers=max_workers, progress=progress
    )
    results_by_id = {r.content_id: r for r in results}
    decision = overall_decision(results)
    logger.info("overall decision for %s %d -> %s: %s", post_type, post_id, target_language, decision)
    if deepseek.usage:
        logger.info(
            "token usage for %s %d: %s (estimated cost: $%.4f)",
            post_type, post_id, deepseek.usage, estimate_cost_usd(deepseek.usage),
        )

    # Payload is always built (even in dry-run/review) since review mode
    # needs the exact WP-write payload to save for later publishing --
    # building it costs nothing extra, it just doesn't get sent anywhere yet.
    payload = build_translation_payload(
        page, post_id, post_type, blocks, all_blocks, elementor_doc, results, results_by_id
    )

    endpoint = f"/wp-json/wp/v2/{'pages' if post_type == 'page' else 'posts'}"

    publish_command = None
    if review_json_path is not None:
        save_review(review_json_path, post_id, post_type, target_language, payload, results)
        publish_command = f"python -m app.cli.publish --review {review_json_path}"
        logger.info("saved review artifact for %s %d to %s", post_type, post_id, review_json_path)

    if dry_run:
        logger.info("dry-run: nothing written for %s %d", post_type, post_id)
        if progress is not None:
            progress.finish(decision, publish_command=publish_command)
        return PageTranslationResult(
            post_id=post_id,
            post_type=post_type,
            target_language=target_language,
            blocks=results,
            overall_decision=decision,
            written=False,
        )

    if decision != "auto_approve":
        flagged = [r.content_id for r in results if r.qa is not None and r.qa.decision != "auto_approve"]
        logger.warning(
            "writing %s %d as draft despite %s decision — %d block(s) need human review before publishing: %s",
            post_type, post_id, decision, len(flagged), flagged,
        )

    translated_post_id = write_and_link_translation(wp_client, endpoint, payload, post_id, post_type, target_language)

    if progress is not None:
        progress.finish(decision)

    return PageTranslationResult(
        post_id=post_id,
        post_type=post_type,
        target_language=target_language,
        blocks=results,
        overall_decision=decision,
        written=True,
        translated_post_id=translated_post_id,
    )


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


def configure_logging() -> None:
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_dir / "translate_audit.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def main() -> None:
    from dotenv import load_dotenv

    load_dotenv()
    configure_logging()

    parser = argparse.ArgumentParser(description="Translate one WordPress page/post end-to-end.")
    parser.add_argument("--post-id", type=int, required=True)
    parser.add_argument("--post-type", choices=["page", "post"], default="page")
    parser.add_argument("--language", default="es")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--workers", type=int, default=5, help="Concurrent DeepSeek calls across blocks (default 5, 1=sequential)"
    )
    parser.add_argument(
        "--no-progress-html",
        action="store_true",
        help="Skip writing logs/progress.html (the local self-refreshing progress page)",
    )
    parser.add_argument(
        "--review",
        action="store_true",
        help=(
            "Translate and save a review artifact (logs/review_<post-id>_<language>.json) instead of "
            "writing to WordPress. Open progress.html to compare source/translation per block, then run "
            "the printed `python -m app.cli.publish ...` command to write the approved draft (no extra "
            "DeepSeek cost). Implies --dry-run."
        ),
    )
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
    if progress_html_path:
        print(f"Live progress: open {progress_html_path.resolve()} in a browser (auto-refreshes every 2s)")

    review_json_path = (
        Path(f"logs/review_{args.post_id}_{args.language}.json") if args.review else None
    )

    result = translate_page(
        wp_client,
        deepseek,
        glossary_entries,
        args.post_id,
        args.post_type,
        args.language,
        dry_run=args.dry_run or args.review,
        max_workers=args.workers,
        progress_html_path=progress_html_path,
        review_json_path=review_json_path,
    )

    print(f"Post {result.post_id} ({result.post_type}) -> {result.target_language}")
    print(f"Overall decision: {result.overall_decision}")
    for block in result.blocks:
        qa_note = f" [{block.qa.decision}, score={block.qa.score}]" if block.qa else " [skipped]"
        print(f"  {block.content_id} ({block.type}){qa_note}")
    if result.written:
        print(f"Written as draft: post id {result.translated_post_id}")
    else:
        print("Nothing written (dry-run or rejected by QA).")
    if deepseek.usage:
        print(f"Token usage: {deepseek.usage}")
        print(f"Estimated cost: ${estimate_cost_usd(deepseek.usage):.4f} USD")


if __name__ == "__main__":
    main()
