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
