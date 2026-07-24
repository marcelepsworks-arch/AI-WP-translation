# Posts/Pages Field Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete FASE 3.5 of `PLA-ACCIO.md` — close the remaining gaps identified in `MAPEIG-CAMPS.md` for posts/pages: `excerpt`, Yoast `og_title`/`og_description`, featured image alt/caption, and category/tag names. None of this depends on WPML.

**Architecture:** `extract_yoast_blocks()` (`app/extraction/seo_extractor.py`) gains `og_title`/`og_description` — a pure extension, automatically benefiting `content_extractor.py` *and* `woocommerce_extractor.py` since both already call it. `extract_page_content()` gains an `excerpt` block plus two new **optional** parameters, `featured_media` and `(categories, tags)`: the WordPress `wp/v2/posts`/`pages` endpoints only return category/tag **IDs** and a `featured_media` **ID**, never the full term/media objects (unlike WooCommerce's `wc/v3/products`, which embeds them) — so a caller who already fetched those objects separately passes them in. Extraction itself stays pure and I/O-free, consistent with the rest of `app/extraction/`.

**Tech Stack:** Python 3.10, `pydantic` v2, `pytest`. No new dependency, no network calls in tests.

## Global Constraints

- `extract_page_content()`'s new parameters default to `None` and change nothing when omitted — existing callers (and all 5 of the module's current tests) must keep passing unmodified.
- Featured image caption is only extracted when non-empty (same rule as everywhere else in the extractor).
- Code and comments in English.

---

### Task 1: `excerpt` block

**Files:**
- Modify: `app/extraction/content_extractor.py`
- Modify: `tests/extraction/test_content_extractor.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `extract_page_content()` now emits an `"excerpt"`-type block when `page["excerpt"]["rendered"]` is non-empty.

- [ ] **Step 1: Write the failing test — append to `tests/extraction/test_content_extractor.py`**

```python
def test_extract_page_content_includes_excerpt_when_present():
    page = _sample_page(excerpt={"rendered": "<p>A short summary of the page.</p>"})

    blocks = extract_page_content(page, id_prefix="page_4309")

    excerpt_blocks = [b for b in blocks if b.type == "excerpt"]
    assert len(excerpt_blocks) == 1
    assert excerpt_blocks[0].source == "A short summary of the page."
    assert excerpt_blocks[0].content_id == "page_4309_excerpt"


def test_extract_page_content_skips_excerpt_when_absent_or_empty():
    page = _sample_page(excerpt={"rendered": ""})

    blocks = extract_page_content(page)

    assert [b for b in blocks if b.type == "excerpt"] == []


def test_extract_page_content_works_without_excerpt_key_at_all():
    # Real WP REST responses always include "excerpt", but extraction
    # must not crash if a caller hands it a partial dict (e.g. in tests).
    page = _sample_page()
    del page["excerpt"]

    blocks = extract_page_content(page)

    assert [b for b in blocks if b.type == "excerpt"] == []
```

Also add the `excerpt` key to the existing `_sample_page()` fixture at the top of the file so unrelated tests keep passing:

```python
def _sample_page(**overrides):
    page = {
        "id": 4309,
        "title": {"rendered": "Precision Agriculture"},
        "content": {"rendered": "<h2>Steering</h2><p>RTK improves steering accuracy.</p>"},
        "excerpt": {"rendered": ""},
    }
    page.update(overrides)
    return page
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/extraction/test_content_extractor.py -v`
Expected: FAIL — `test_extract_page_content_includes_excerpt_when_present` fails (no excerpt block emitted yet); other tests still pass.

- [ ] **Step 3: Modify `app/extraction/content_extractor.py`**

Add right after the title block, before the Yoast call:

```python
    excerpt = page.get("excerpt", {}).get("rendered", "").strip()
    if excerpt:
        from bs4 import BeautifulSoup

        excerpt_text = BeautifulSoup(excerpt, "html.parser").get_text(separator=" ", strip=True)
        if excerpt_text:
            blocks.append(
                ContentBlock(
                    content_id=f"{prefix}_excerpt",
                    type="excerpt",
                    context=title,
                    source=excerpt_text,
                    translate=not is_protected_content(excerpt_text),
                )
            )
```

(Move the `from bs4 import BeautifulSoup` import to the top of the file with the other imports instead of inline — inline imports are only shown here for the diff; the actual file edit puts it at module level.)

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/extraction/test_content_extractor.py -v`
Expected: 8 passed (5 existing + 3 new).

- [ ] **Step 5: Commit and push**

```bash
git add app/extraction/content_extractor.py tests/extraction/test_content_extractor.py
git commit -m "feat: extract page/post excerpt as a translatable block"
git push origin master
```

---

### Task 2: Yoast `og_title` / `og_description`

**Files:**
- Modify: `app/extraction/seo_extractor.py`
- Modify: `tests/extraction/test_seo_extractor.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `extract_yoast_blocks()` now also emits `"og_title"` / `"og_description"` blocks when present. Both `content_extractor.py` and `woocommerce_extractor.py` get this automatically since they already call this function.

- [ ] **Step 1: Write the failing test — append to `tests/extraction/test_seo_extractor.py`**

```python
def test_extract_yoast_blocks_includes_og_title_and_og_description():
    yoast = {
        "title": "Precision Agriculture - Precision GNSS",
        "description": "RTK for Agriculture.",
        "og_title": "Precision Agriculture",
        "og_description": "Learn how RTK helps farming.",
    }

    blocks = extract_yoast_blocks(yoast, id_prefix="page_4309")

    types = [b.type for b in blocks]
    assert types == ["seo_title", "seo_description", "og_title", "og_description"]
    assert blocks[2].source == "Precision Agriculture"
    assert blocks[2].content_id == "page_4309_og_title"
    assert blocks[3].source == "Learn how RTK helps farming."


def test_extract_yoast_blocks_skips_og_fields_when_absent():
    yoast = {"title": "Only title", "description": "Only description"}

    blocks = extract_yoast_blocks(yoast, id_prefix="page_1")

    assert len(blocks) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/extraction/test_seo_extractor.py -v`
Expected: FAIL — the two new tests fail (only 2 blocks produced, no `og_title`/`og_description`).

- [ ] **Step 3: Modify `app/extraction/seo_extractor.py`**

Replace the full file with:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/extraction/test_seo_extractor.py -v`
Expected: 5 passed (3 existing + 2 new).

- [ ] **Step 5: Run content_extractor and woocommerce_extractor tests to confirm nothing broke**

Run: `.venv/Scripts/python.exe -m pytest tests/extraction/test_content_extractor.py tests/extraction/test_woocommerce_extractor.py -v`
Expected: all still passing (neither test fixture includes `og_title`/`og_description`, so block counts there are unchanged).

- [ ] **Step 6: Commit and push**

```bash
git add app/extraction/seo_extractor.py tests/extraction/test_seo_extractor.py
git commit -m "feat: extract Yoast og_title/og_description (shared by posts/pages and products)"
git push origin master
```

---

### Task 3: Featured image alt/caption (optional pre-fetched param)

**Files:**
- Modify: `app/extraction/content_extractor.py`
- Modify: `tests/extraction/test_content_extractor.py`

**Interfaces:**
- Consumes: nothing new (takes a plain dict shaped like a `wp/v2/media/{id}` response — the caller is responsible for fetching it, e.g. via `app.wordpress.content` in a future orchestrator).
- Produces: `extract_page_content(page, id_prefix=None, featured_media=None)` — new optional parameter.

- [ ] **Step 1: Write the failing test — append to `tests/extraction/test_content_extractor.py`**

```python
def test_extract_page_content_includes_featured_media_alt_when_provided():
    featured_media = {"id": 55, "alt_text": "Tractor with RTK antenna in a field", "caption": {"rendered": ""}}

    blocks = extract_page_content(_sample_page(), id_prefix="page_4309", featured_media=featured_media)

    alt_blocks = [b for b in blocks if b.type == "alt_text"]
    assert len(alt_blocks) == 1
    assert alt_blocks[0].source == "Tractor with RTK antenna in a field"
    assert alt_blocks[0].content_id == "page_4309_featured_media_55_alt"


def test_extract_page_content_includes_featured_media_caption_when_present():
    featured_media = {"id": 55, "alt_text": "", "caption": {"rendered": "<p>A tractor in a field.</p>"}}

    blocks = extract_page_content(_sample_page(), id_prefix="page_4309", featured_media=featured_media)

    caption_blocks = [b for b in blocks if b.type == "caption"]
    assert len(caption_blocks) == 1
    assert caption_blocks[0].source == "A tractor in a field."


def test_extract_page_content_ignores_featured_media_when_not_provided():
    blocks = extract_page_content(_sample_page())

    assert [b for b in blocks if b.type in ("alt_text", "caption")] == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/extraction/test_content_extractor.py -v`
Expected: FAIL — `TypeError: extract_page_content() got an unexpected keyword argument 'featured_media'`.

- [ ] **Step 3: Modify `app/extraction/content_extractor.py`**

Change the function signature and add the block right before the `body_html` line:

```python
def extract_page_content(
    page: dict,
    id_prefix: str | None = None,
    featured_media: dict | None = None,
) -> list[ContentBlock]:
    prefix = id_prefix or f"page_{page['id']}"
    blocks: list[ContentBlock] = []

    # ... existing title / excerpt / yoast blocks unchanged ...

    if featured_media:
        media_id = featured_media.get("id", 0)
        alt_text = (featured_media.get("alt_text") or "").strip()
        if alt_text:
            blocks.append(
                ContentBlock(
                    content_id=f"{prefix}_featured_media_{media_id}_alt",
                    type="alt_text",
                    context=title,
                    source=alt_text,
                    translate=not is_protected_content(alt_text),
                )
            )
        caption_html = featured_media.get("caption", {}).get("rendered", "")
        caption_text = BeautifulSoup(caption_html, "html.parser").get_text(separator=" ", strip=True)
        if caption_text:
            blocks.append(
                ContentBlock(
                    content_id=f"{prefix}_featured_media_{media_id}_caption",
                    type="caption",
                    context=title,
                    source=caption_text,
                    translate=not is_protected_content(caption_text),
                )
            )

    body_html = page["content"]["rendered"]
    blocks.extend(extract_blocks(body_html, id_prefix=prefix))

    return blocks
```

Add `from bs4 import BeautifulSoup` to the module's top-level imports (used by both this block and the excerpt block from Task 1 — consolidate into a single import).

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/extraction/test_content_extractor.py -v`
Expected: 11 passed (8 from Task 1 + 3 new).

- [ ] **Step 5: Commit and push**

```bash
git add app/extraction/content_extractor.py tests/extraction/test_content_extractor.py
git commit -m "feat: extract featured image alt text and caption (optional, pre-fetched)"
git push origin master
```

---

### Task 4: Categories and tags (optional pre-fetched param)

**Files:**
- Modify: `app/extraction/content_extractor.py`
- Modify: `tests/extraction/test_content_extractor.py`

**Interfaces:**
- Consumes: `extract_taxonomy_terms()` (existing, from `app.extraction.taxonomy_extractor`).
- Produces: `extract_page_content(page, id_prefix=None, featured_media=None, categories=None, tags=None)` — two more optional parameters, each a list of term dicts (`wp/v2/categories`/`tags` shape) the caller already fetched.

- [ ] **Step 1: Write the failing test — append to `tests/extraction/test_content_extractor.py`**

```python
def test_extract_page_content_includes_categories_and_tags_when_provided():
    categories = [{"id": 8, "name": "RTK Applications"}]
    tags = [{"id": 3, "name": "Precision Agriculture"}]

    blocks = extract_page_content(
        _sample_page(), id_prefix="page_4309", categories=categories, tags=tags
    )

    assert any(b.type == "category_name" and b.source == "RTK Applications" for b in blocks)
    assert any(b.type == "tag_name" and b.source == "Precision Agriculture" for b in blocks)


def test_extract_page_content_ignores_categories_and_tags_when_not_provided():
    blocks = extract_page_content(_sample_page())

    assert [b for b in blocks if b.type in ("category_name", "tag_name")] == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/extraction/test_content_extractor.py -v`
Expected: FAIL — `TypeError: extract_page_content() got an unexpected keyword argument 'categories'`.

- [ ] **Step 3: Modify `app/extraction/content_extractor.py`**

Add `categories`/`tags` parameters and, at the end of the function, before `return blocks`:

```python
def extract_page_content(
    page: dict,
    id_prefix: str | None = None,
    featured_media: dict | None = None,
    categories: list[dict] | None = None,
    tags: list[dict] | None = None,
) -> list[ContentBlock]:
    # ... (Task 1-3 body unchanged) ...

    if categories:
        blocks.extend(extract_taxonomy_terms(categories, id_prefix=prefix, term_type="category"))
    if tags:
        blocks.extend(extract_taxonomy_terms(tags, id_prefix=prefix, term_type="tag"))

    return blocks
```

Add `from app.extraction.taxonomy_extractor import extract_taxonomy_terms` to the imports.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/extraction/test_content_extractor.py -v`
Expected: 13 passed.

- [ ] **Step 5: Run the full project test suite**

Run: `.venv/Scripts/python.exe -m pytest -v`
Expected: all tests pass (154 existing + 3 + 2 + 3 + 2 = 164 total).

- [ ] **Step 6: Commit and push**

```bash
git add app/extraction/content_extractor.py tests/extraction/test_content_extractor.py
git commit -m "feat: extract post/page category and tag names (optional, pre-fetched)"
git push origin master
```

---

### Task 5: Update tracking docs

**Files:**
- Modify: `MAPEIG-CAMPS.md`
- Modify: `PLA-ACCIO.md`
- Modify: `LOG.md`

- [ ] **Step 1:** Update `MAPEIG-CAMPS.md` sections 1-4 to mark `excerpt`, `og_title`/`og_description`, featured media alt/caption, and category/tag names as "done."
- [ ] **Step 2:** Mark `PLA-ACCIO.md` FASE 3.5 as done, noting that `featured_media`/`categories`/`tags` are optional parameters a future orchestrator must fetch and pass in (extraction itself stays I/O-free).
- [ ] **Step 3:** Add a `LOG.md` entry.
- [ ] **Step 4: Commit and push**

```bash
git add MAPEIG-CAMPS.md PLA-ACCIO.md LOG.md docs/superpowers/plans/2026-07-24-posts-pages-field-expansion.md
git commit -m "docs: mark FASE 3.5 done, log posts/pages field expansion session"
git push origin master
```

---

## Out of scope for this plan

- Actually fetching `featured_media`/`categories`/`tags` from WordPress — that's a FASE 8 orchestration concern (or an incremental `app/wordpress/` addition), not extraction logic. This plan only makes `extract_page_content()` *able* to use that data once a caller supplies it.
- Media `title.rendered`/`description.rendered` — flagged as low priority in `MAPEIG-CAMPS.md` §4 (rarely user-visible); skipped here to keep this plan focused on what's actually visible content.
