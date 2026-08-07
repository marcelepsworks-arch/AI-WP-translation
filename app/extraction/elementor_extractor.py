"""Faithful Elementor `_elementor_data` round-trip (FASE 3.3).

Elementor stores a page's real layout/content in the `_elementor_data`
postmeta as a JSON array of nested "elements" (section/column/container/
widget, each with an `elements` list of children). `post_content` is only a
secondary rendered copy Elementor keeps in sync — translating it alone does
not change the page's actual layout, images, or widget structure.

This module extracts only the translatable *text* out of known widget
settings into ContentBlocks (everything else — ids, elType, widgetType,
styling settings, structure, image urls/ids — is left completely
untouched), and re-inserts translations back into a full copy of the
original tree, so the rebuilt `_elementor_data` is structurally identical
to the original except for the translated text.

Unknown/unlisted widget types are left alone entirely rather than guessed
at — safer to under-translate a widget than to corrupt one whose settings
shape isn't known.
"""
from __future__ import annotations

import json
from typing import Callable

from app.extraction.html_parser import extract_blocks
from app.extraction.protected_content import is_protected_content
from app.extraction.schemas import ContentBlock

# widgetType -> plain-text setting keys (value is a translatable string, used as-is).
_PLAIN_TEXT_FIELDS: dict[str, list[str]] = {
    "heading": ["title"],
    "button": ["text"],
    "icon-box": ["title_text", "description_text"],
    "image-box": ["title_text", "description_text"],
    "call-to-action": ["title", "description", "button_text"],
    "counter": ["title"],
    "alert": ["alert_title", "alert_description"],
    "testimonial": ["testimonial_content", "testimonial_name", "testimonial_job"],
}

# widgetType -> HTML-bearing setting keys (rich text, broken into blocks like a page body).
_HTML_FIELDS: dict[str, list[str]] = {
    "text-editor": ["editor"],
}

# widgetType -> (settings key holding a list, [item text sub-keys]).
_LIST_FIELDS: dict[str, tuple[str, list[str]]] = {
    "icon-list": ("icon_list", ["text"]),
    "tabs": ("tabs", ["tab_title", "tab_content"]),
    "accordion": ("tabs", ["tab_title", "tab_content"]),
}

# widgetType -> setting key holding {"url":..., "id":..., "alt":...}; only "alt" is translatable.
_IMAGE_FIELDS: dict[str, list[str]] = {
    "image": ["image"],
    "image-box": ["image"],
}


def _reassemble_fragment(blocks: list[ContentBlock], translations: dict[str, str]) -> str:
    parts: list[str] = []
    for block in blocks:
        text = translations.get(block.content_id, block.source)
        if not text.strip():
            continue
        tag = "h2" if block.type == "heading" else "p"
        parts.append(f"<{tag}>{text}</{tag}>")
    return "\n".join(parts)


class ElementorDocument:
    """A parsed `_elementor_data` tree plus the translatable blocks found in
    it. Keeps live references into the parsed structure so translations can
    be written straight back in, then re-serialized with `to_json()`.
    """

    def __init__(self, elements: list[dict]) -> None:
        self.elements = elements
        self.blocks: list[ContentBlock] = []
        self._setters: list[Callable[[dict[str, str]], None]] = []

    def apply_translations(self, translations: dict[str, str]) -> None:
        for setter in self._setters:
            setter(translations)

    def to_json(self) -> str:
        return json.dumps(self.elements)

    def _add_plain_field(self, settings: dict, key: str, widget_type: str, value: str) -> None:
        if not value.strip() or is_protected_content(value):
            return
        content_id = f"elementor_{len(self.blocks) + 1}"
        self.blocks.append(
            ContentBlock(content_id=content_id, type=f"elementor_{widget_type}_{key}", context="", source=value, translate=True)
        )

        def setter(translations: dict[str, str], _settings=settings, _key=key, _id=content_id) -> None:
            if _id in translations:
                _settings[_key] = translations[_id]

        self._setters.append(setter)

    def _add_html_field(self, settings: dict, key: str, widget_type: str, value: str) -> None:
        if not value.strip():
            return
        prefix = f"elementor_{len(self.blocks) + 1}_html"
        sub_blocks = extract_blocks(value, id_prefix=prefix)
        if not sub_blocks:
            return
        self.blocks.extend(sub_blocks)

        def setter(translations: dict[str, str], _settings=settings, _key=key, _blocks=sub_blocks) -> None:
            _settings[_key] = _reassemble_fragment(_blocks, translations)

        self._setters.append(setter)


def _walk(nodes: list[dict], doc: ElementorDocument) -> None:
    for node in nodes:
        widget_type = node.get("widgetType")
        settings = node.get("settings")

        if widget_type and isinstance(settings, dict):
            for key in _PLAIN_TEXT_FIELDS.get(widget_type, []):
                value = settings.get(key)
                if isinstance(value, str):
                    doc._add_plain_field(settings, key, widget_type, value)

            for key in _HTML_FIELDS.get(widget_type, []):
                value = settings.get(key)
                if isinstance(value, str):
                    doc._add_html_field(settings, key, widget_type, value)

            if widget_type in _LIST_FIELDS:
                list_key, item_keys = _LIST_FIELDS[widget_type]
                items = settings.get(list_key)
                if isinstance(items, list):
                    for item in items:
                        if not isinstance(item, dict):
                            continue
                        for item_key in item_keys:
                            value = item.get(item_key)
                            if isinstance(value, str):
                                doc._add_plain_field(item, item_key, widget_type, value)

            for key in _IMAGE_FIELDS.get(widget_type, []):
                image = settings.get(key)
                if isinstance(image, dict):
                    alt = image.get("alt")
                    if isinstance(alt, str):
                        doc._add_plain_field(image, "alt", f"{widget_type}_image", alt)

        children = node.get("elements")
        if isinstance(children, list):
            _walk(children, doc)


def parse_elementor_document(raw_json: str) -> ElementorDocument | None:
    """Parses `_elementor_data` into an ElementorDocument, or None if the
    JSON is missing/invalid — callers should fall back to plain-HTML body
    extraction in that case, never fail the whole page translation.
    """
    if not raw_json or not raw_json.strip():
        return None
    try:
        elements = json.loads(raw_json)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(elements, list):
        return None

    doc = ElementorDocument(elements)
    _walk(elements, doc)
    return doc
