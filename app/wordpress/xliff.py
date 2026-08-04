"""XLIFF adapter: converts between WPML's XLIFF 1.2 export format and the
project's own ContentBlock schema (app/extraction/schemas.py), so the
existing extraction/translation/QA pipeline never has to know about XLIFF.

WPML's real XLIFF export has not been validated yet — WPML is not installed
on staging (see MEMORIA.md 2026-08-04, PLA-ACCIO.md task 1.8). This module
targets the standard XLIFF 1.2 schema and tolerates both the namespaced and
un-namespaced trans-unit forms until a real export is available to check
against.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET

from app.extraction.schemas import ContentBlock

XLIFF_NAMESPACE = "urn:oasis:names:tc:xliff:document:1.2"
ET.register_namespace("", XLIFF_NAMESPACE)


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _namespace_prefix(tag: str) -> str:
    return tag.rsplit("}", 1)[0] + "}" if tag.startswith("{") else ""


def _find_child(element: ET.Element, local_name: str) -> ET.Element | None:
    return next((child for child in element if _local_name(child.tag) == local_name), None)


def parse_xliff(xliff_content: str) -> list[ContentBlock]:
    root = ET.fromstring(xliff_content)
    blocks: list[ContentBlock] = []
    for trans_unit in root.iter():
        if _local_name(trans_unit.tag) != "trans-unit":
            continue
        source_el = _find_child(trans_unit, "source")
        if source_el is None or not (source_el.text or "").strip():
            continue
        blocks.append(
            ContentBlock(
                content_id=trans_unit.get("id", ""),
                type="xliff_segment",
                context=trans_unit.get("resname", ""),
                source=source_el.text or "",
                translate=True,
            )
        )
    return blocks


def build_translated_xliff(xliff_content: str, translations: dict[str, str]) -> str:
    root = ET.fromstring(xliff_content)
    for trans_unit in root.iter():
        if _local_name(trans_unit.tag) != "trans-unit":
            continue
        content_id = trans_unit.get("id", "")
        if content_id not in translations:
            continue

        target_el = _find_child(trans_unit, "target")
        if target_el is None:
            source_el = _find_child(trans_unit, "source")
            source_idx = list(trans_unit).index(source_el)
            target_el = ET.Element(_namespace_prefix(trans_unit.tag) + "target")
            trans_unit.insert(source_idx + 1, target_el)

        target_el.text = translations[content_id]

    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode")
