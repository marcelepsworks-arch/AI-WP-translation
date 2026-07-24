"""Extracts translatable Yoast SEO fields from a WordPress REST API
`yoast_head_json` object. Shared by posts/pages and WooCommerce
products — Yoast treats every post type identically.
"""
from __future__ import annotations

from app.extraction.protected_content import is_protected_content
from app.extraction.schemas import ContentBlock

_FIELD_TO_BLOCK_TYPE = {
    "title": "seo_title",
    "description": "seo_description",
    "og_title": "og_title",
    "og_description": "og_description",
}


def extract_yoast_blocks(
    yoast_head_json: dict | None,
    id_prefix: str,
    context: str = "",
) -> list[ContentBlock]:
    if not yoast_head_json:
        return []

    blocks: list[ContentBlock] = []

    for field, block_type in _FIELD_TO_BLOCK_TYPE.items():
        value = (yoast_head_json.get(field) or "").strip()
        if not value:
            continue
        blocks.append(
            ContentBlock(
                content_id=f"{id_prefix}_{block_type}",
                type=block_type,
                context=context,
                source=value,
                translate=not is_protected_content(value),
            )
        )

    return blocks
