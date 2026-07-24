"""Extracts translatable Yoast SEO fields from a WordPress REST API
`yoast_head_json` object. Shared by posts/pages and WooCommerce
products — Yoast treats every post type identically.
"""
from __future__ import annotations

from app.extraction.protected_content import is_protected_content
from app.extraction.schemas import ContentBlock


def extract_yoast_blocks(
    yoast_head_json: dict | None,
    id_prefix: str,
    context: str = "",
) -> list[ContentBlock]:
    if not yoast_head_json:
        return []

    blocks: list[ContentBlock] = []

    seo_title = (yoast_head_json.get("title") or "").strip()
    if seo_title:
        blocks.append(
            ContentBlock(
                content_id=f"{id_prefix}_seo_title",
                type="seo_title",
                context=context,
                source=seo_title,
                translate=not is_protected_content(seo_title),
            )
        )

    seo_description = (yoast_head_json.get("description") or "").strip()
    if seo_description:
        blocks.append(
            ContentBlock(
                content_id=f"{id_prefix}_seo_description",
                type="seo_description",
                context=context,
                source=seo_description,
                translate=not is_protected_content(seo_description),
            )
        )

    return blocks
