"""Orchestrates extraction of all translatable blocks from one
WordPress REST API page/post dict: title, SEO fields (when exposed),
and the parsed body.
"""
from __future__ import annotations

from app.extraction.html_parser import extract_blocks
from app.extraction.protected_content import is_protected_content
from app.extraction.schemas import ContentBlock


def extract_page_content(page: dict, id_prefix: str | None = None) -> list[ContentBlock]:
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

    yoast = page.get("yoast_head_json")
    if yoast:
        seo_title = (yoast.get("title") or "").strip()
        if seo_title:
            blocks.append(
                ContentBlock(
                    content_id=f"{prefix}_seo_title",
                    type="seo_title",
                    context=title,
                    source=seo_title,
                    translate=not is_protected_content(seo_title),
                )
            )
        seo_description = (yoast.get("description") or "").strip()
        if seo_description:
            blocks.append(
                ContentBlock(
                    content_id=f"{prefix}_seo_description",
                    type="seo_description",
                    context=title,
                    source=seo_description,
                    translate=not is_protected_content(seo_description),
                )
            )

    body_html = page["content"]["rendered"]
    blocks.extend(extract_blocks(body_html, id_prefix=prefix))

    return blocks
