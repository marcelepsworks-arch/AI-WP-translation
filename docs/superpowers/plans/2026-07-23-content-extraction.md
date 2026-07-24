# Content Extraction Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete FASE 3.1/3.2/3.4 of `PLA-ACCIO.md`: convert a WordPress page/post's rendered HTML into the semantic content blocks defined by the brief (section 6: `content_id`/`type`/`context`/`source`/`translate`), explicitly protecting URLs, emails, and shortcodes from being marked translatable (brief section 7.2), validated against real pages already fetched from `staging.precision-gnss.com` in the previous session.

**Architecture:** Three small, composable pieces: `is_protected_content()` (a pure text classifier), `ContentBlock` (the Pydantic schema for one extracted unit), and `extract_blocks()` (walks parsed HTML in document order, tracking a heading breadcrumb for `context`). `extract_page_content()` orchestrates these against a real WordPress REST API page/post dict (title + rendered body + Yoast SEO fields when present), producing the full ordered block list for that page. FASE 3.3 (reduced Elementor JSON dry-run counter) is out of scope for this plan — `_elementor_data` is not exposed via REST on this site (`AUDITORIA-INICIAL.md` §0.5), so there is nothing real to parse yet; extraction instead works off the rendered HTML, which Elementor itself outputs and which is available for every page today.

**Tech Stack:** Python 3.10, `beautifulsoup4` (new dependency — already used ad hoc earlier this session, now formalized), `pydantic` v2, `pytest`. No network calls in the automated suite; a manual script re-uses the real staging pages already fetched in FASE 2 for an end-to-end sanity check.

## Global Constraints

- A block whose entire text is a bare URL, email address, or WordPress shortcode is extracted with `translate: false` — never silently dropped, never marked translatable (brief section 7.2).
- A block with no text content at all (after stripping) is not emitted at all — it carries no information either way.
- `context` is built from the nearest preceding heading hierarchy (e.g. `"RTK Applications > Precision Agriculture"`), matching the brief's example in section 6.
- Code and comments in English.

---

## File Structure

```
app/extraction/
├── __init__.py
├── protected_content.py   # is_protected_content()
├── schemas.py              # ContentBlock
├── html_parser.py          # extract_blocks()
└── content_extractor.py    # extract_page_content()

tests/extraction/
├── __init__.py
├── test_protected_content.py
├── test_schemas.py
├── test_html_parser.py
└── test_content_extractor.py

scripts/
└── extract_staging_page.py   # manual smoke test against a real staging page
```

---

### Task 1: Protected content detection

**Files:**
- Create: `app/extraction/__init__.py`
- Create: `app/extraction/protected_content.py`
- Create: `tests/extraction/__init__.py`
- Create: `tests/extraction/test_protected_content.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `is_protected_content(text: str) -> bool`. Task 3 (`html_parser.py`) calls this per block.

- [ ] **Step 1: Create package init files**

`app/extraction/__init__.py`:
```python
```

`tests/extraction/__init__.py`:
```python
```

- [ ] **Step 2: Write the failing test — `tests/extraction/test_protected_content.py`**

```python
import pytest

from app.extraction.protected_content import is_protected_content


@pytest.mark.parametrize(
    "text",
    [
        "https://www.precision-gnss.com/rtk-application/archaeology/",
        "http://example.com",
        "www.ardusimple.com",
        "support@precision-gnss.com",
        "[contact-form-7 id=\"123\"]",
        "",
        "   ",
    ],
)
def test_is_protected_content_flags_urls_emails_shortcodes_and_empty_text(text):
    assert is_protected_content(text) is True


@pytest.mark.parametrize(
    "text",
    [
        "The ZED-F9P module delivers 1 cm RTK accuracy.",
        "Learn more",
        "Contact us at our office for more information.",
        "Base station setup takes about 8 seconds.",
    ],
)
def test_is_protected_content_does_not_flag_normal_prose(text):
    assert is_protected_content(text) is False


def test_is_protected_content_flags_url_even_with_surrounding_whitespace():
    assert is_protected_content("  https://example.com/page/  ") is True
```

- [ ] **Step 3: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/extraction/test_protected_content.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.extraction.protected_content'`.

- [ ] **Step 4: Write minimal implementation — `app/extraction/protected_content.py`**

```python
"""Detects text that must never be sent for translation as-is: bare
URLs, email addresses, WordPress shortcodes, and empty text.

Matches the "protected content" rules in the project brief, section 7.2.
Does NOT flag prose containing a technical term or product name — that
is the glossary's job (app/translation/glossary.py), not extraction's.
"""
from __future__ import annotations

import re

_URL_PATTERN = re.compile(r"^(https?://|www\.)\S+$", re.IGNORECASE)
_EMAIL_PATTERN = re.compile(r"^[\w.+-]+@[\w-]+\.[\w.-]+$")
_SHORTCODE_PATTERN = re.compile(r"^\[.+\]$")


def is_protected_content(text: str) -> bool:
    stripped = text.strip()

    if not stripped:
        return True
    if _URL_PATTERN.match(stripped):
        return True
    if _EMAIL_PATTERN.match(stripped):
        return True
    if _SHORTCODE_PATTERN.match(stripped):
        return True

    return False
```

- [ ] **Step 5: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/extraction/test_protected_content.py -v`
Expected: 12 passed.

- [ ] **Step 6: Commit and push**

```bash
git add app/extraction/__init__.py app/extraction/protected_content.py tests/extraction/__init__.py tests/extraction/test_protected_content.py
git commit -m "feat: add is_protected_content() for URL/email/shortcode detection"
git push origin master
```

---

### Task 2: `ContentBlock` schema

**Files:**
- Create: `app/extraction/schemas.py`
- Create: `tests/extraction/test_schemas.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `ContentBlock(content_id: str, type: str, context: str, source: str, translate: bool)`. Task 3 constructs these.

- [ ] **Step 1: Write the failing test — `tests/extraction/test_schemas.py`**

```python
import pytest
from pydantic import ValidationError

from app.extraction.schemas import ContentBlock


def test_content_block_holds_all_required_fields():
    block = ContentBlock(
        content_id="page_4309_block_3",
        type="paragraph",
        context="RTK Applications > Precision Agriculture",
        source="RTK GNSS delivers 1 cm accuracy.",
        translate=True,
    )

    assert block.content_id == "page_4309_block_3"
    assert block.type == "paragraph"
    assert block.context == "RTK Applications > Precision Agriculture"
    assert block.source == "RTK GNSS delivers 1 cm accuracy."
    assert block.translate is True


def test_content_block_requires_content_id():
    with pytest.raises(ValidationError):
        ContentBlock(type="paragraph", context="", source="text", translate=True)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/extraction/test_schemas.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.extraction.schemas'`.

- [ ] **Step 3: Write minimal implementation — `app/extraction/schemas.py`**

```python
"""Semantic content block schema, matching the project brief section 6:
{"content_id": "...", "type": "...", "context": "...", "source": "...", "translate": true}
"""
from __future__ import annotations

from pydantic import BaseModel


class ContentBlock(BaseModel):
    content_id: str
    type: str
    context: str
    source: str
    translate: bool
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/extraction/test_schemas.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit and push**

```bash
git add app/extraction/schemas.py tests/extraction/test_schemas.py
git commit -m "feat: add ContentBlock schema"
git push origin master
```

---

### Task 3: HTML block extractor

**Files:**
- Create: `app/extraction/html_parser.py`
- Create: `tests/extraction/test_html_parser.py`

**Interfaces:**
- Consumes: `is_protected_content()` (Task 1), `ContentBlock` (Task 2).
- Produces: `extract_blocks(html: str, id_prefix: str = "block") -> list[ContentBlock]`. Task 4 calls this for the page body.

- [ ] **Step 1: Write the failing test — `tests/extraction/test_html_parser.py`**

```python
from app.extraction.html_parser import extract_blocks


def test_extract_blocks_extracts_heading_and_paragraph():
    html = "<h2>Precision Agriculture</h2><p>RTK GNSS delivers 1 cm accuracy.</p>"

    blocks = extract_blocks(html)

    assert len(blocks) == 2
    assert blocks[0].type == "heading"
    assert blocks[0].source == "Precision Agriculture"
    assert blocks[1].type == "paragraph"
    assert blocks[1].source == "RTK GNSS delivers 1 cm accuracy."


def test_extract_blocks_builds_context_from_preceding_heading():
    html = "<h2>Precision Agriculture</h2><p>First point.</p><h3>Steering</h3><p>Second point.</p>"

    blocks = extract_blocks(html)

    paragraphs = [b for b in blocks if b.type == "paragraph"]
    assert paragraphs[0].context == "Precision Agriculture"
    assert paragraphs[1].context == "Precision Agriculture > Steering"


def test_extract_blocks_extracts_list_items_and_blockquotes():
    html = "<ul><li>First</li><li>Second</li></ul><blockquote>A quote.</blockquote>"

    blocks = extract_blocks(html)

    types = [b.type for b in blocks]
    assert types == ["list_item", "list_item", "blockquote"]
    assert [b.source for b in blocks] == ["First", "Second", "A quote."]


def test_extract_blocks_extracts_standalone_cta_button_not_inside_paragraph():
    html = '<div class="elementor-button-wrapper"><a href="/products/simple-rtk2b/">Learn more</a></div>'

    blocks = extract_blocks(html)

    assert len(blocks) == 1
    assert blocks[0].type == "button"
    assert blocks[0].source == "Learn more"


def test_extract_blocks_does_not_duplicate_link_text_already_inside_paragraph():
    html = '<p>Read the <a href="/docs/">documentation</a> for details.</p>'

    blocks = extract_blocks(html)

    assert len(blocks) == 1
    assert blocks[0].type == "paragraph"
    assert blocks[0].source == "Read the documentation for details."


def test_extract_blocks_extracts_image_alt_text():
    html = '<img src="/wp-content/uploads/photo.png" alt="RTK base station in a field" />'

    blocks = extract_blocks(html)

    assert len(blocks) == 1
    assert blocks[0].type == "alt_text"
    assert blocks[0].source == "RTK base station in a field"


def test_extract_blocks_skips_images_without_alt_text():
    html = '<img src="/wp-content/uploads/photo.png" alt="" />'

    blocks = extract_blocks(html)

    assert blocks == []


def test_extract_blocks_marks_bare_url_paragraph_as_not_translatable():
    html = "<p>https://www.precision-gnss.com/contact-us/</p>"

    blocks = extract_blocks(html)

    assert len(blocks) == 1
    assert blocks[0].translate is False


def test_extract_blocks_skips_script_and_style_content_entirely():
    html = "<script>console.log('hi')</script><style>.foo{color:red}</style><p>Real text.</p>"

    blocks = extract_blocks(html)

    assert len(blocks) == 1
    assert blocks[0].source == "Real text."


def test_extract_blocks_assigns_sequential_content_ids_with_prefix():
    html = "<h2>Title</h2><p>Body.</p>"

    blocks = extract_blocks(html, id_prefix="page_4309")

    assert blocks[0].content_id == "page_4309_block_1"
    assert blocks[1].content_id == "page_4309_block_2"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/extraction/test_html_parser.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.extraction.html_parser'`.

- [ ] **Step 3: Write minimal implementation — `app/extraction/html_parser.py`**

```python
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


def _block_type_for_heading() -> str:
    return "heading"


def _block_type_for_tag(tag_name: str) -> str:
    if tag_name == "li":
        return "list_item"
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

        if tag.name in _HEADING_TAGS:
            level = int(tag.name[1])
            heading_stack[:] = [h for h in heading_stack if h[0] < level]
            counter += 1
            blocks.append(
                ContentBlock(
                    content_id=f"{id_prefix}_block_{counter}",
                    type=_block_type_for_heading(),
                    context=current_context(),
                    source=text,
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
                source=text,
                translate=not is_protected_content(text),
            )
        )

    return blocks
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/extraction/test_html_parser.py -v`
Expected: 10 passed.

- [ ] **Step 5: Commit and push**

```bash
git add app/extraction/html_parser.py tests/extraction/test_html_parser.py
git commit -m "feat: add extract_blocks() HTML-to-semantic-block extractor"
git push origin master
```

---

### Task 4: Page-level orchestration

**Files:**
- Create: `app/extraction/content_extractor.py`
- Create: `tests/extraction/test_content_extractor.py`

**Interfaces:**
- Consumes: `extract_blocks()` (Task 3), `ContentBlock` (Task 2). Input is a WordPress REST API page/post dict as returned by `app.wordpress.content.get_page()`/`get_post()`.
- Produces: `extract_page_content(page: dict, id_prefix: str) -> list[ContentBlock]`. FASE 4/8 (future) will feed this output into `DeepSeekClient.translate()` per block.

- [ ] **Step 1: Write the failing test — `tests/extraction/test_content_extractor.py`**

```python
from app.extraction.content_extractor import extract_page_content


def _sample_page(**overrides):
    page = {
        "id": 4309,
        "title": {"rendered": "Precision Agriculture"},
        "content": {"rendered": "<h2>Steering</h2><p>RTK improves steering accuracy.</p>"},
    }
    page.update(overrides)
    return page


def test_extract_page_content_includes_title_as_first_block():
    blocks = extract_page_content(_sample_page(), id_prefix="page_4309")

    assert blocks[0].type == "title"
    assert blocks[0].source == "Precision Agriculture"
    assert blocks[0].content_id == "page_4309_title"


def test_extract_page_content_includes_body_blocks_after_title():
    blocks = extract_page_content(_sample_page(), id_prefix="page_4309")

    body_types = [b.type for b in blocks[1:]]
    assert body_types == ["heading", "paragraph"]


def test_extract_page_content_includes_seo_fields_when_present():
    page = _sample_page(
        yoast_head_json={
            "title": "Precision Agriculture - Precision GNSS",
            "description": "RTK for Agriculture. Learn how steering works.",
        }
    )

    blocks = extract_page_content(page, id_prefix="page_4309")

    seo_blocks = [b for b in blocks if b.type in ("seo_title", "seo_description")]
    assert len(seo_blocks) == 2
    assert any(b.source == "Precision Agriculture - Precision GNSS" for b in seo_blocks)
    assert any(b.source == "RTK for Agriculture. Learn how steering works." for b in seo_blocks)


def test_extract_page_content_skips_seo_fields_when_absent():
    blocks = extract_page_content(_sample_page(), id_prefix="page_4309")

    seo_blocks = [b for b in blocks if b.type in ("seo_title", "seo_description")]
    assert seo_blocks == []


def test_extract_page_content_uses_page_id_as_default_prefix():
    blocks = extract_page_content(_sample_page())

    assert blocks[0].content_id == "page_4309_title"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/extraction/test_content_extractor.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.extraction.content_extractor'`.

- [ ] **Step 3: Write minimal implementation — `app/extraction/content_extractor.py`**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/extraction/test_content_extractor.py -v`
Expected: 5 passed.

- [ ] **Step 5: Run the full project test suite**

Run: `.venv/Scripts/python.exe -m pytest -v`
Expected: all tests pass (74 existing + 12 + 2 + 10 + 5 = 103 total).

- [ ] **Step 6: Commit and push**

```bash
git add app/extraction/content_extractor.py tests/extraction/test_content_extractor.py
git commit -m "feat: add extract_page_content() to orchestrate title/SEO/body extraction"
git push origin master
```

---

### Task 5: Manual smoke test against real staging content

**Files:**
- Create: `scripts/extract_staging_page.py`

**Interfaces:**
- Consumes: `WordPressClient`, `get_page` (from FASE 2); `extract_page_content` (Task 4).

- [ ] **Step 1: Create `scripts/extract_staging_page.py`**

```python
"""Manual smoke test: extract semantic content blocks from one real
staging page and print them.

Usage:
    python scripts/extract_staging_page.py <page_id>

Reads credentials from .env — never hardcode them here.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

from app.extraction.content_extractor import extract_page_content
from app.wordpress.client import WordPressClient
from app.wordpress.content import get_page


def main() -> None:
    load_dotenv()

    page_id = int(sys.argv[1]) if len(sys.argv) > 1 else 4309  # Precision Agriculture

    client = WordPressClient(
        base_url=os.environ["STAGING_URL"],
        basic_auth=(os.environ["STAGING_BASIC_AUTH_USER"], os.environ["STAGING_BASIC_AUTH_PASSWORD"]),
        wp_username=os.environ.get("WP_USERNAME"),
        wp_app_password=os.environ.get("WP_APPLICATION_PASSWORD"),
    )

    page = get_page(client, page_id)
    blocks = extract_page_content(page)

    translatable = [b for b in blocks if b.translate]
    protected = [b for b in blocks if not b.translate]

    print(f"Page: {page['title']['rendered']} (id={page_id})")
    print(f"Total blocks: {len(blocks)}  |  translatable: {len(translatable)}  |  protected/skipped: {len(protected)}")
    print()
    for block in blocks[:20]:
        flag = "T" if block.translate else "-"
        context = f" [{block.context}]" if block.context else ""
        print(f"[{flag}] {block.type:<15}{context}  {block.source[:80]}")
    if len(blocks) > 20:
        print(f"... and {len(blocks) - 20} more blocks")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify the script is syntactically valid**

Run: `.venv/Scripts/python.exe -m py_compile scripts/extract_staging_page.py`
Expected: no output, exit code 0.

- [ ] **Step 3: Run it against the real staging site and eyeball the output**

Run: `.venv/Scripts/python.exe scripts/extract_staging_page.py 4309`
Expected: a list of blocks from the real "Precision Agriculture" page, headings/paragraphs with sensible context breadcrumbs, no bare URLs marked translatable.

- [ ] **Step 4: Commit and push**

```bash
git add scripts/extract_staging_page.py
git commit -m "chore: add manual content-extraction smoke script"
git push origin master
```

---

### Task 6: Update tracking docs

**Files:**
- Modify: `requirements.txt`
- Modify: `PLA-ACCIO.md`
- Modify: `LOG.md`

- [ ] **Step 1:** Add `beautifulsoup4>=4.12.0` to `requirements.txt`.
- [ ] **Step 2:** Mark `PLA-ACCIO.md` FASE 3.1, 3.2, 3.4 as done; note 3.3 (Elementor JSON dry-run) as deferred since `_elementor_data` isn't exposed on this site.
- [ ] **Step 3:** Add a `LOG.md` entry, including real findings from Task 5's output (block counts, any surprises).
- [ ] **Step 4: Commit and push**

```bash
git add requirements.txt PLA-ACCIO.md LOG.md docs/superpowers/plans/2026-07-23-content-extraction.md
git commit -m "docs: mark FASE 3.1/3.2/3.4 done, log content extraction session"
git push origin master
```

---

## Out of scope for this plan

- FASE 3.3 (Elementor JSON widget-count dry-run) — `_elementor_data` not exposed via REST on this site; revisit once the `gnss-bridge` mu-plugin (FASE 1, blocked on WPML) exposes it, or if WPML's own Elementor integration makes it available.
- Wiring extracted blocks into `DeepSeekClient.translate()`/chunking — that is FASE 8 orchestration, still blocked on WPML for the write-back half of the pipeline.
