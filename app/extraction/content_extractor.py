"""Orchestrates extraction of all translatable blocks from one
WordPress REST API page/post dict: title, excerpt, SEO fields (when
exposed), and the parsed body.
"""
from __future__ import annotations

from bs4 import BeautifulSoup

from app.extraction.html_parser import extract_blocks
from app.extraction.protected_content import is_protected_content
from app.extraction.schemas import ContentBlock
from app.extraction.seo_extractor import extract_yoast_blocks
from app.extraction.taxonomy_extractor import extract_taxonomy_terms


def extract_page_content(
    page: dict,
    id_prefix: str | None = None,
    featured_media: dict | None = None,
    categories: list[dict] | None = None,
    tags: list[dict] | None = None,
    skip_body: bool = False,
) -> list[ContentBlock]:
    prefix = id_prefix or f"page_{page['id']}"
    blocks: list[ContentBlock] = []

    title = page["title"]["rendered"].strip()
    if title:
        blocks.append(
            ContentBlock(
                content_id=f"{prefix}_title",
                type="title",
                context="",
                source=title,
                translate=not is_protected_content(title),
            )
        )

    excerpt_html = page.get("excerpt", {}).get("rendered", "")
    excerpt_text = BeautifulSoup(excerpt_html, "html.parser").get_text(separator=" ", strip=True)
    if excerpt_text:
        blocks.append(
            ContentBlock(
                content_id=f"{prefix}_excerpt",
                type="excerpt",
                context=title,
                source=excerpt_text,
                translate=not is_protected_content(excerpt_text),
            )
        )

    blocks.extend(extract_yoast_blocks(page.get("yoast_head_json"), id_prefix=prefix, context=title))

    if featured_media:
        media_id = featured_media.get("id", 0)
        alt_text = (featured_media.get("alt_text") or "").strip()
        if alt_text:
            blocks.append(
                ContentBlock(
                    content_id=f"{prefix}_featured_media_{media_id}_alt",
                    type="alt_text",
                    context=title,
                    source=alt_text,
                    translate=not is_protected_content(alt_text),
                )
            )
        caption_html = featured_media.get("caption", {}).get("rendered", "")
        caption_text = BeautifulSoup(caption_html, "html.parser").get_text(separator=" ", strip=True)
        if caption_text:
            blocks.append(
                ContentBlock(
                    content_id=f"{prefix}_featured_media_{media_id}_caption",
                    type="caption",
                    context=title,
                    source=caption_text,
                    translate=not is_protected_content(caption_text),
                )
            )

    if not skip_body:
        body_html = page["content"]["rendered"]
        blocks.extend(extract_blocks(body_html, id_prefix=prefix))

    if categories:
        blocks.extend(extract_taxonomy_terms(categories, id_prefix=prefix, term_type="category"))
    if tags:
        blocks.extend(extract_taxonomy_terms(tags, id_prefix=prefix, term_type="tag"))

    return blocks
