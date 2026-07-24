"""Extracts translatable content from a WooCommerce product (the
wc/v3/products REST schema — not wp/v2). Generic: works against any
WordPress + WooCommerce site, not tied to any specific one.

Fields that are NEVER extracted, even as protected blocks (per
MAPEIG-CAMPS.md section 6.7): sku, price, regular_price, sale_price,
stock_quantity, stock_status, weight, dimensions, and the same fields
on each entry in `variations`.
"""
from __future__ import annotations

from app.extraction.html_parser import extract_blocks
from app.extraction.protected_content import is_protected_content
from app.extraction.schemas import ContentBlock
from app.extraction.seo_extractor import extract_yoast_blocks
from app.extraction.taxonomy_extractor import extract_taxonomy_terms


def extract_product_content(product: dict, id_prefix: str | None = None) -> list[ContentBlock]:
    prefix = id_prefix or f"product_{product['id']}"
    blocks: list[ContentBlock] = []

    name = (product.get("name") or "").strip()
    if name:
        blocks.append(
            ContentBlock(
                content_id=f"{prefix}_name",
                type="title",
                context="",
                source=name,
                translate=not is_protected_content(name),
            )
        )

    blocks.extend(extract_yoast_blocks(product.get("yoast_head_json"), id_prefix=prefix, context=name))

    short_description = product.get("short_description") or ""
    if short_description.strip():
        blocks.extend(extract_blocks(short_description, id_prefix=f"{prefix}_short_description"))

    description = product.get("description") or ""
    if description.strip():
        blocks.extend(extract_blocks(description, id_prefix=f"{prefix}_description"))

    purchase_note = (product.get("purchase_note") or "").strip()
    if purchase_note:
        blocks.append(
            ContentBlock(
                content_id=f"{prefix}_purchase_note",
                type="purchase_note",
                context=name,
                source=purchase_note,
                translate=not is_protected_content(purchase_note),
            )
        )

    for attribute in product.get("attributes", []):
        attr_id = attribute.get("id", 0)
        attr_name = (attribute.get("name") or "").strip()
        if attr_name:
            blocks.append(
                ContentBlock(
                    content_id=f"{prefix}_attribute_{attr_id}_name",
                    type="attribute_name",
                    context=name,
                    source=attr_name,
                    translate=not is_protected_content(attr_name),
                )
            )
        for index, option in enumerate(attribute.get("options", []), start=1):
            option_text = str(option).strip()
            if option_text:
                blocks.append(
                    ContentBlock(
                        content_id=f"{prefix}_attribute_{attr_id}_option_{index}",
                        type="attribute_value",
                        context=f"{name} > {attr_name}",
                        source=option_text,
                        translate=not is_protected_content(option_text),
                    )
                )

    for image in product.get("images", []):
        alt_text = (image.get("alt") or "").strip()
        if alt_text:
            blocks.append(
                ContentBlock(
                    content_id=f"{prefix}_image_{image.get('id', 0)}_alt",
                    type="alt_text",
                    context=name,
                    source=alt_text,
                    translate=not is_protected_content(alt_text),
                )
            )

    blocks.extend(extract_taxonomy_terms(product.get("categories", []), id_prefix=prefix, term_type="category"))
    blocks.extend(extract_taxonomy_terms(product.get("tags", []), id_prefix=prefix, term_type="tag"))

    return blocks
