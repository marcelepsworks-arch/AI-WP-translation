# WooCommerce Product Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement generic, reusable extraction of translatable content from WooCommerce products (`wc/v3/products` REST schema), per `MAPEIG-CAMPS.md` section 6 — not tied to `precision-gnss.com` (which has no WooCommerce), but written to work against any WordPress site running WooCommerce, per the user's explicit request to support "other WordPress sites with WooCommerce."

**Architecture:** Two new pieces, plus one DRY refactor. `app/extraction/taxonomy_extractor.py` is a generic function that turns any list of WordPress/WooCommerce taxonomy terms (categories, tags, product attributes-as-terms) into `ContentBlock`s — reusable for posts/pages taxonomies later (`PLA-ACCIO.md` task 3.5) as well as products now. `app/extraction/seo_extractor.py` extracts `yoast_head_json` into blocks — extracted out of `content_extractor.py` (pure refactor, no behavior change) so products and posts/pages share identical Yoast handling instead of duplicating it. `app/extraction/woocommerce_extractor.py` orchestrates a full product: name, short/long description (via the existing `extract_blocks()` HTML walker — WooCommerce descriptions are WYSIWYG HTML, same shape as post content), purchase note, attributes/options, image alt text, categories, and tags.

**Tech Stack:** Python 3.10, `pydantic` v2, `pytest`. No live WooCommerce site exists in scope, so tests use hand-built fixture dicts that mirror the documented, stable `wc/v3/products` schema — flagged in `MAPEIG-CAMPS.md` as pending real-site validation.

## Global Constraints

- Never reference `precision-gnss.com` or any site-specific detail in this code — it must work against the standard WooCommerce REST schema for any site.
- Never mark `sku`, `price`, `regular_price`, `sale_price`, `stock_quantity`, `weight`, `dimensions`, or any variation's `sku`/`price` as translatable — these are never extracted at all, not even as protected blocks (per `MAPEIG-CAMPS.md` 6.7).
- Reviews/user-generated content are explicitly out of scope — the WooCommerce REST product object doesn't include review bodies anyway (they're a separate `wc/v3/products/reviews` endpoint), so this is automatically respected as long as nothing new goes fetch that endpoint.
- Code and comments in English.

---

## File Structure

```
app/extraction/
├── taxonomy_extractor.py    # extract_taxonomy_terms()
├── seo_extractor.py           # extract_yoast_blocks()
├── content_extractor.py        # MODIFIED: use seo_extractor internally
└── woocommerce_extractor.py     # extract_product_content()

tests/extraction/
├── test_taxonomy_extractor.py
├── test_seo_extractor.py
└── test_woocommerce_extractor.py
```

---

### Task 1: Generic taxonomy term extractor

**Files:**
- Create: `app/extraction/taxonomy_extractor.py`
- Create: `tests/extraction/test_taxonomy_extractor.py`

**Interfaces:**
- Consumes: `is_protected_content()`, `ContentBlock` (existing).
- Produces: `extract_taxonomy_terms(terms: list[dict], id_prefix: str, term_type: str) -> list[ContentBlock]`. Task 4 (`woocommerce_extractor.py`) calls this for `categories` and `tags`; a future FASE 3.5 increment will call it for post/page categories and tags too.

- [ ] **Step 1: Write the failing test — `tests/extraction/test_taxonomy_extractor.py`**

```python
from app.extraction.taxonomy_extractor import extract_taxonomy_terms


def test_extract_taxonomy_terms_creates_name_block_per_term():
    terms = [{"id": 1, "name": "RTK Receivers"}, {"id": 2, "name": "Antennas"}]

    blocks = extract_taxonomy_terms(terms, id_prefix="product_10", term_type="category")

    assert len(blocks) == 2
    assert blocks[0].type == "category_name"
    assert blocks[0].source == "RTK Receivers"
    assert blocks[0].content_id == "product_10_category_1_name"


def test_extract_taxonomy_terms_includes_description_block_when_present():
    terms = [{"id": 1, "name": "RTK Receivers", "description": "High-precision GNSS receivers."}]

    blocks = extract_taxonomy_terms(terms, id_prefix="product_10", term_type="category")

    descriptions = [b for b in blocks if b.type == "category_description"]
    assert len(descriptions) == 1
    assert descriptions[0].source == "High-precision GNSS receivers."
    assert descriptions[0].context == "RTK Receivers"


def test_extract_taxonomy_terms_skips_empty_description():
    terms = [{"id": 1, "name": "Antennas", "description": ""}]

    blocks = extract_taxonomy_terms(terms, id_prefix="product_10", term_type="category")

    assert [b.type for b in blocks] == ["category_name"]


def test_extract_taxonomy_terms_works_for_tags_too():
    terms = [{"id": 5, "name": "Bluetooth"}]

    blocks = extract_taxonomy_terms(terms, id_prefix="product_10", term_type="tag")

    assert blocks[0].type == "tag_name"
    assert blocks[0].content_id == "product_10_tag_5_name"


def test_extract_taxonomy_terms_returns_empty_list_for_no_terms():
    assert extract_taxonomy_terms([], id_prefix="product_10", term_type="category") == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/extraction/test_taxonomy_extractor.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.extraction.taxonomy_extractor'`.

- [ ] **Step 3: Write minimal implementation — `app/extraction/taxonomy_extractor.py`**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/extraction/test_taxonomy_extractor.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit and push**

```bash
git add app/extraction/taxonomy_extractor.py tests/extraction/test_taxonomy_extractor.py
git commit -m "feat: add generic taxonomy term extractor (categories, tags)"
git push origin master
```

---

### Task 2: Extract Yoast SEO block logic out of content_extractor.py

**Files:**
- Create: `app/extraction/seo_extractor.py`
- Create: `tests/extraction/test_seo_extractor.py`
- Modify: `app/extraction/content_extractor.py`

**Interfaces:**
- Consumes: `is_protected_content()`, `ContentBlock` (existing).
- Produces: `extract_yoast_blocks(yoast_head_json: dict | None, id_prefix: str, context: str = "") -> list[ContentBlock]`. Both `content_extractor.py` (posts/pages) and `woocommerce_extractor.py` (Task 4) call this — one implementation, not two copies.

- [ ] **Step 1: Write the failing test — `tests/extraction/test_seo_extractor.py`**

```python
from app.extraction.seo_extractor import extract_yoast_blocks


def test_extract_yoast_blocks_returns_title_and_description():
    yoast = {"title": "Precision Agriculture - Precision GNSS", "description": "RTK for Agriculture."}

    blocks = extract_yoast_blocks(yoast, id_prefix="page_4309", context="Precision Agriculture")

    types = [b.type for b in blocks]
    assert types == ["seo_title", "seo_description"]
    assert blocks[0].source == "Precision Agriculture - Precision GNSS"
    assert blocks[0].content_id == "page_4309_seo_title"
    assert blocks[0].context == "Precision Agriculture"


def test_extract_yoast_blocks_returns_empty_list_when_yoast_is_none():
    assert extract_yoast_blocks(None, id_prefix="page_1") == []


def test_extract_yoast_blocks_skips_missing_fields():
    blocks = extract_yoast_blocks({"title": "Only a title"}, id_prefix="page_1")

    assert len(blocks) == 1
    assert blocks[0].type == "seo_title"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/extraction/test_seo_extractor.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.extraction.seo_extractor'`.

- [ ] **Step 3: Write minimal implementation — `app/extraction/seo_extractor.py`**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/extraction/test_seo_extractor.py -v`
Expected: 3 passed.

- [ ] **Step 5: Refactor `app/extraction/content_extractor.py` to use it (pure refactor — no behavior change)**

Replace the Yoast block in `extract_page_content`:

```python
"""Orchestrates extraction of all translatable blocks from one
WordPress REST API page/post dict: title, SEO fields (when exposed),
and the parsed body.
"""
from __future__ import annotations

from app.extraction.html_parser import extract_blocks
from app.extraction.protected_content import is_protected_content
from app.extraction.schemas import ContentBlock
from app.extraction.seo_extractor import extract_yoast_blocks


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

    blocks.extend(extract_yoast_blocks(page.get("yoast_head_json"), id_prefix=prefix, context=title))

    body_html = page["content"]["rendered"]
    blocks.extend(extract_blocks(body_html, id_prefix=prefix))

    return blocks
```

- [ ] **Step 6: Run the existing content_extractor tests to confirm the refactor didn't break anything**

Run: `.venv/Scripts/python.exe -m pytest tests/extraction/test_content_extractor.py -v`
Expected: 5 passed (same 5 as before — this step proves the refactor is behavior-preserving).

- [ ] **Step 7: Commit and push**

```bash
git add app/extraction/seo_extractor.py tests/extraction/test_seo_extractor.py app/extraction/content_extractor.py
git commit -m "refactor: extract Yoast SEO block logic into shared seo_extractor module"
git push origin master
```

---

### Task 3: WooCommerce product extractor

**Files:**
- Create: `app/extraction/woocommerce_extractor.py`
- Create: `tests/extraction/test_woocommerce_extractor.py`

**Interfaces:**
- Consumes: `extract_blocks()` (existing), `extract_yoast_blocks()` (Task 2), `extract_taxonomy_terms()` (Task 1), `is_protected_content()`, `ContentBlock`.
- Produces: `extract_product_content(product: dict, id_prefix: str | None = None) -> list[ContentBlock]`. Input is a `wc/v3/products/{id}` REST response dict.

- [ ] **Step 1: Write the failing test — `tests/extraction/test_woocommerce_extractor.py`**

```python
from app.extraction.woocommerce_extractor import extract_product_content


def _sample_product(**overrides) -> dict:
    product = {
        "id": 101,
        "name": "SimpleRTK3B Starter Kit",
        "description": "<h2>Overview</h2><p>A complete RTK starter kit with 1 cm accuracy.</p>",
        "short_description": "<p>Everything you need to get started with RTK.</p>",
        "sku": "SRTK3B-KIT",
        "price": "199.00",
        "regular_price": "199.00",
        "purchase_note": "",
        "attributes": [],
        "images": [],
        "categories": [],
        "tags": [],
    }
    product.update(overrides)
    return product


def test_extract_product_content_includes_name_as_title_block():
    blocks = extract_product_content(_sample_product(), id_prefix="product_101")

    assert blocks[0].type == "title"
    assert blocks[0].source == "SimpleRTK3B Starter Kit"
    assert blocks[0].content_id == "product_101_name"


def test_extract_product_content_never_extracts_sku_or_price():
    blocks = extract_product_content(_sample_product())

    all_sources = [b.source for b in blocks]
    assert "SRTK3B-KIT" not in all_sources
    assert "199.00" not in all_sources


def test_extract_product_content_extracts_long_and_short_description_as_html_blocks():
    blocks = extract_product_content(_sample_product(), id_prefix="product_101")

    headings = [b for b in blocks if b.type == "heading"]
    paragraphs = [b for b in blocks if b.type == "paragraph"]
    assert headings[0].source == "Overview"
    assert any(b.source == "A complete RTK starter kit with 1 cm accuracy." for b in paragraphs)
    assert any(b.source == "Everything you need to get started with RTK." for b in paragraphs)


def test_extract_product_content_includes_purchase_note_when_present():
    product = _sample_product(purchase_note="Thank you! Your activation code will arrive by email.")

    blocks = extract_product_content(product, id_prefix="product_101")

    notes = [b for b in blocks if b.type == "purchase_note"]
    assert len(notes) == 1
    assert notes[0].source == "Thank you! Your activation code will arrive by email."


def test_extract_product_content_extracts_attribute_names_and_options():
    product = _sample_product(
        attributes=[{"id": 1, "name": "Color", "options": ["Black", "White"]}]
    )

    blocks = extract_product_content(product, id_prefix="product_101")

    attr_names = [b for b in blocks if b.type == "attribute_name"]
    attr_values = [b for b in blocks if b.type == "attribute_value"]
    assert attr_names[0].source == "Color"
    assert [b.source for b in attr_values] == ["Black", "White"]
    assert attr_values[0].context == "SimpleRTK3B Starter Kit > Color"


def test_extract_product_content_extracts_image_alt_text():
    product = _sample_product(images=[{"id": 55, "alt": "SimpleRTK3B kit box contents"}])

    blocks = extract_product_content(product, id_prefix="product_101")

    alt_blocks = [b for b in blocks if b.type == "alt_text"]
    assert len(alt_blocks) == 1
    assert alt_blocks[0].source == "SimpleRTK3B kit box contents"


def test_extract_product_content_skips_images_without_alt_text():
    product = _sample_product(images=[{"id": 55, "alt": ""}])

    blocks = extract_product_content(product)

    assert [b for b in blocks if b.type == "alt_text"] == []


def test_extract_product_content_includes_categories_and_tags():
    product = _sample_product(
        categories=[{"id": 8, "name": "RTK Receivers"}],
        tags=[{"id": 3, "name": "Bluetooth"}],
    )

    blocks = extract_product_content(product, id_prefix="product_101")

    assert any(b.type == "category_name" and b.source == "RTK Receivers" for b in blocks)
    assert any(b.type == "tag_name" and b.source == "Bluetooth" for b in blocks)


def test_extract_product_content_includes_seo_fields_when_present():
    product = _sample_product(
        yoast_head_json={"title": "SimpleRTK3B Kit - ArduSimple", "description": "Buy the SimpleRTK3B kit."}
    )

    blocks = extract_product_content(product, id_prefix="product_101")

    seo_blocks = [b for b in blocks if b.type in ("seo_title", "seo_description")]
    assert len(seo_blocks) == 2


def test_extract_product_content_uses_product_id_as_default_prefix():
    blocks = extract_product_content(_sample_product())

    assert blocks[0].content_id == "product_101_name"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/extraction/test_woocommerce_extractor.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.extraction.woocommerce_extractor'`.

- [ ] **Step 3: Write minimal implementation — `app/extraction/woocommerce_extractor.py`**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/extraction/test_woocommerce_extractor.py -v`
Expected: 11 passed.

- [ ] **Step 5: Run the full project test suite**

Run: `.venv/Scripts/python.exe -m pytest -v`
Expected: all tests pass (136 existing + 5 + 3 + 11 = 155 total).

- [ ] **Step 6: Commit and push**

```bash
git add app/extraction/woocommerce_extractor.py tests/extraction/test_woocommerce_extractor.py
git commit -m "feat: add generic WooCommerce product content extractor"
git push origin master
```

---

### Task 4: Update tracking docs

**Files:**
- Modify: `MAPEIG-CAMPS.md`
- Modify: `PLA-ACCIO.md`
- Modify: `LOG.md`

- [ ] **Step 1:** Update `MAPEIG-CAMPS.md` section 6 to mark the fields as "implemented (generic, unvalidated against a real site)" rather than "not built."
- [ ] **Step 2:** Add a new item to `PLA-ACCIO.md` FASE 3 (or a new "FASE 3-WC" subsection) documenting `extract_product_content()` as done, generic, and pending real-site validation.
- [ ] **Step 3:** Add a `LOG.md` entry.
- [ ] **Step 4: Commit and push**

```bash
git add MAPEIG-CAMPS.md PLA-ACCIO.md LOG.md docs/superpowers/plans/2026-07-24-woocommerce-extraction.md
git commit -m "docs: mark WooCommerce product extraction implemented, pending real-site validation"
git push origin master
```

---

## Out of scope for this plan

- Reviews/ratings — explicitly excluded per `MAPEIG-CAMPS.md` 6.2 (user-generated content).
- Custom, plugin-specific product tabs — impossible to build generically without a real site to inspect; each plugin stores this differently.
- Variation-level descriptions (`variations[].description`) — rare in practice; add if a real site needs it.
- Wiring this into `app/wordpress/content.py` (a `get_product()` fetch function) — no WooCommerce site exists yet to fetch from; this plan covers the pure extraction logic only, ready to be wired in the moment a real site is available.
