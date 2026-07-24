"""Generic extraction of translatable content from WordPress/WooCommerce
taxonomy terms (categories, tags, product attribute terms). Reusable
across post/page taxonomies and WooCommerce product categories/tags —
the term shape (id, name, optional description) is identical everywhere.
"""
from __future__ import annotations

from app.extraction.protected_content import is_protected_content
from app.extraction.schemas import ContentBlock


def extract_taxonomy_terms(
    terms: list[dict],
    id_prefix: str,
    term_type: str,
) -> list[ContentBlock]:
    blocks: list[ContentBlock] = []

    for term in terms:
        term_id = term.get("id", 0)
        name = (term.get("name") or "").strip()

        if name:
            blocks.append(
                ContentBlock(
                    content_id=f"{id_prefix}_{term_type}_{term_id}_name",
                    type=f"{term_type}_name",
                    context="",
                    source=name,
                    translate=not is_protected_content(name),
                )
            )

        description = (term.get("description") or "").strip()
        if description:
            blocks.append(
                ContentBlock(
                    content_id=f"{id_prefix}_{term_type}_{term_id}_description",
                    type=f"{term_type}_description",
                    context=name,
                    source=description,
                    translate=not is_protected_content(description),
                )
            )

    return blocks
