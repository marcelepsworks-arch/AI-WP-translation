from app.extraction.content_extractor import extract_page_content


def _sample_page(**overrides):
    page = {
        "id": 4309,
        "title": {"rendered": "Precision Agriculture"},
        "content": {"rendered": "<h2>Steering</h2><p>RTK improves steering accuracy.</p>"},
        "excerpt": {"rendered": ""},
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


def test_extract_page_content_skip_body_omits_content_rendered_blocks():
    blocks = extract_page_content(_sample_page(), id_prefix="page_4309", skip_body=True)

    assert [b.type for b in blocks] == ["title"]


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
