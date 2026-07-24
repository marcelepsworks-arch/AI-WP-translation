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
