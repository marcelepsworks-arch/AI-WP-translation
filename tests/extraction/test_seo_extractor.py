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
