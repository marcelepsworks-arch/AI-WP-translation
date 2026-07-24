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
