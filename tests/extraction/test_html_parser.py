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
