"""Verifies that the inline HTML skeleton of a block survives translation,
and repairs the one failure mode that is safe to repair automatically.

Blocks are handed to DeepSeek as raw inner HTML (`tag.decode_contents()`
in app/extraction/html_parser.py), so a paragraph arrives as
`... use 2x <a href="...">Basic Starter Kits</a> or ...`. Translator
prompt rule 15 asks for every tag to come back untouched and in the same
position relative to the text -- but, exactly like the `<script>` case in
html_sanitizer.py, that is a request, not a guarantee.

The four original QA signals cannot see a violation of it. If the model
returns `2x<a href="...">Kits Basicos</a>`, the number is still 2, the
glossary is respected, the href is byte-identical and the meaning is
unchanged -- so numbers, terminology, URLs and the Reviewer all pass, the
block scores 100 and auto-approves, and the page renders "2xKits
Basicos". This module is the signal that closes that gap.

Two distinct defects, deliberately treated differently:

- The tag skeleton changed (a tag dropped, invented, or its attributes
  altered). Not repairable without guessing where the tag belonged in a
  sentence whose word order has changed, so it is reported and penalised.
- The skeleton is intact but a space next to a tag boundary was lost.
  Repairable with certainty: the tags correspond one-to-one, and putting
  back a space the source already had cannot change meaning.

Only a *lost* space is repaired, never a gained one -- a translation that
reorders a sentence around a tag legitimately gains spaces, and treating
that as a defect would flag correct work.
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup
from pydantic import BaseModel

from app.qa.html_sanitizer import sanitize_html

_TAG_PATTERN = re.compile(r"<[^>]+>")
_TAG_NAME_PATTERN = re.compile(r"</?\s*([a-zA-Z0-9]+)")


def _skeleton(html: str) -> list[tuple[str, tuple[tuple[str, str], ...]]]:
    """Ordered (tag name, normalized attributes) pairs. Attributes are
    sorted so a model that reorders them is not reported as a defect.
    """
    soup = BeautifulSoup(html, "html.parser")
    skeleton = []
    for tag in soup.find_all(True):
        attrs = tuple(
            sorted(
                (name, " ".join(value) if isinstance(value, list) else str(value))
                for name, value in tag.attrs.items()
            )
        )
        skeleton.append((tag.name, attrs))
    return skeleton


def _classify(char: str | None) -> str:
    if char is None:
        return "edge"
    if char.isspace():
        return "space"
    if char in "<>":
        return "tag"
    if char.isalnum():
        return "word"
    return "punct"


def _boundaries(html: str) -> list[tuple[str, int, str, int, str]]:
    """For every tag: (label, offset-before, class-before, offset-after,
    class-after), where the offsets are where a space would go.
    """
    result = []
    for match in _TAG_PATTERN.finditer(html):
        name_match = _TAG_NAME_PATTERN.match(match.group())
        if not name_match:
            continue
        closing = match.group().startswith("</")
        label = f"<{'/' if closing else ''}{name_match.group(1)}>"
        start, end = match.start(), match.end()
        result.append(
            (
                label,
                start,
                _classify(html[start - 1] if start > 0 else None),
                end,
                _classify(html[end] if end < len(html) else None),
            )
        )
    return result


class HtmlStructureResult(BaseModel):
    passed: bool
    tag_skeleton_matches: bool
    repaired: bool
    glued_boundaries: list[str]
    repaired_translation: str


def check_html_structure(source_html: str, translated_html: str) -> HtmlStructureResult:
    """Compares both sides through `sanitize_html()` so the comparison is
    like-for-like: the translation has already been sanitized by the time
    it reaches QA, while the source never is, and the sanitizer both
    normalizes attribute quoting and drops attributes outside its
    allowlist (`class`, `style`, ...). Comparing the raw strings would
    report every styled `<span>` in the source as a lost attribute.
    """
    source = sanitize_html(source_html)
    translated = sanitize_html(translated_html)

    if _skeleton(source) != _skeleton(translated):
        return HtmlStructureResult(
            passed=False,
            tag_skeleton_matches=False,
            repaired=False,
            glued_boundaries=[],
            repaired_translation=translated_html,
        )

    glued: list[str] = []
    insert_at: list[int] = []
    for (label, _, source_before, _, source_after), (
        _,
        translated_start,
        translated_before,
        translated_end,
        translated_after,
    ) in zip(_boundaries(source), _boundaries(translated)):
        if source_before == "space" and translated_before == "word":
            glued.append(f"before {label}")
            insert_at.append(translated_start)
        if source_after == "space" and translated_after == "word":
            glued.append(f"after {label}")
            insert_at.append(translated_end)

    if not glued:
        return HtmlStructureResult(
            passed=True,
            tag_skeleton_matches=True,
            repaired=False,
            glued_boundaries=[],
            repaired_translation=translated_html,
        )

    repaired = translated
    for offset in sorted(insert_at, reverse=True):  # right to left, so earlier offsets stay valid
        repaired = f"{repaired[:offset]} {repaired[offset:]}"

    return HtmlStructureResult(
        passed=True,
        tag_skeleton_matches=True,
        repaired=True,
        glued_boundaries=glued,
        repaired_translation=repaired,
    )
