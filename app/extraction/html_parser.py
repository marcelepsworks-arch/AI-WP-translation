"""Walks rendered WordPress/Elementor HTML in document order and emits
semantic ContentBlocks, tracking a heading breadcrumb for context.

Elementor's editor output is plain HTML (headings, paragraphs, lists,
buttons, images) — this works directly against that, without needing
the raw _elementor_data JSON (which is not exposed via REST on this
site; see AUDITORIA-INICIAL.md section 0.5).
"""
from __future__ import annotations

from bs4 import BeautifulSoup
from bs4.element import Tag

from app.extraction.protected_content import is_protected_content
from app.extraction.schemas import ContentBlock

_HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
_TEXT_BLOCK_TAGS = {"p", "li", "blockquote"}
_CTA_TAGS = {"a", "button"}
_SKIP_TAGS = {"script", "style"}


def _block_type_for_tag(tag_name: str) -> str:
    if tag_name == "li":
        return "list_item"
    if tag_name == "p":
        return "paragraph"
    if tag_name in _CTA_TAGS:
        return "button"
    return tag_name


def _is_inside_text_block(tag: Tag) -> bool:
    return any(
        parent.name in _TEXT_BLOCK_TAGS or parent.name in _HEADING_TAGS
        for parent in tag.parents
        if isinstance(parent, Tag)
    )


def extract_blocks(html: str, id_prefix: str = "block") -> list[ContentBlock]:
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(_SKIP_TAGS):
        tag.decompose()

    heading_stack: list[tuple[int, str]] = []
    blocks: list[ContentBlock] = []
    counter = 0

    def current_context() -> str:
        return " > ".join(text for _level, text in heading_stack)

    selector = list(_HEADING_TAGS | _TEXT_BLOCK_TAGS | {"img"}) + ["a", "button"]
    for tag in soup.find_all(selector):
        if tag.name == "img":
            alt_text = (tag.get("alt") or "").strip()
            if not alt_text:
                continue
            counter += 1
            blocks.append(
                ContentBlock(
                    content_id=f"{id_prefix}_block_{counter}",
                    type="alt_text",
                    context=current_context(),
                    source=alt_text,
                    translate=not is_protected_content(alt_text),
                )
            )
            continue

        if tag.name in _CTA_TAGS and _is_inside_text_block(tag):
            continue  # already covered by the enclosing paragraph/list item/heading

        text = tag.get_text(separator=" ", strip=True)
        if not text:
            continue

        # Inner HTML (not plain get_text()) so inline formatting -- <strong>,
        # <em>, <a href="...">-- survives translation instead of being
        # silently stripped. The plain-text `text` above is still what
        # decides emptiness/protected-content, since matching those against
        # raw HTML would be unreliable.
        source_html = tag.decode_contents().strip() or text

        if tag.name in _HEADING_TAGS:
            level = int(tag.name[1])
            heading_stack[:] = [h for h in heading_stack if h[0] < level]
            counter += 1
            blocks.append(
                ContentBlock(
                    content_id=f"{id_prefix}_block_{counter}",
                    type="heading",
                    context=current_context(),
                    source=source_html,
                    translate=not is_protected_content(text),
                )
            )
            heading_stack.append((level, text))
            continue

        counter += 1
        blocks.append(
            ContentBlock(
                content_id=f"{id_prefix}_block_{counter}",
                type=_block_type_for_tag(tag.name),
                context=current_context(),
                source=source_html,
                translate=not is_protected_content(text),
            )
        )

    return blocks
