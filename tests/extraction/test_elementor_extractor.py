import json

from app.extraction.elementor_extractor import parse_elementor_document


def _doc(elements: list[dict]):
    return parse_elementor_document(json.dumps(elements))


def test_parse_returns_none_for_empty_or_missing_data():
    assert parse_elementor_document("") is None
    assert parse_elementor_document(None) is None


def test_parse_returns_none_for_invalid_json():
    assert parse_elementor_document("not json") is None


def test_parse_returns_none_when_top_level_is_not_a_list():
    assert parse_elementor_document(json.dumps({"content": []})) is None


def test_extracts_heading_widget_title():
    doc = _doc([{"id": "a1", "elType": "widget", "widgetType": "heading", "settings": {"title": "Precision Agriculture"}}])

    assert len(doc.blocks) == 1
    assert doc.blocks[0].source == "Precision Agriculture"
    assert doc.blocks[0].type == "elementor_heading_title"


def test_extracts_nested_widgets_inside_sections_and_columns():
    doc = _doc([
        {
            "id": "sec1", "elType": "section", "settings": {},
            "elements": [
                {
                    "id": "col1", "elType": "column", "settings": {},
                    "elements": [
                        {"id": "w1", "elType": "widget", "widgetType": "heading", "settings": {"title": "Nested title"}},
                    ],
                }
            ],
        }
    ])

    assert len(doc.blocks) == 1
    assert doc.blocks[0].source == "Nested title"


def test_extracts_button_text():
    doc = _doc([{"id": "b1", "elType": "widget", "widgetType": "button", "settings": {"text": "Get Started"}}])

    assert doc.blocks[0].source == "Get Started"


def test_extracts_text_editor_as_html_sub_blocks():
    doc = _doc([{
        "id": "te1", "elType": "widget", "widgetType": "text-editor",
        "settings": {"editor": "<p>First paragraph.</p><h2>A heading</h2>"},
    }])

    sources = [b.source for b in doc.blocks]
    assert "First paragraph." in sources
    assert "A heading" in sources


def test_extracts_icon_list_items():
    doc = _doc([{
        "id": "il1", "elType": "widget", "widgetType": "icon-list",
        "settings": {"icon_list": [{"text": "First point"}, {"text": "Second point"}]},
    }])

    sources = sorted(b.source for b in doc.blocks)
    assert sources == ["First point", "Second point"]


def test_extracts_tabs_title_and_content():
    doc = _doc([{
        "id": "tb1", "elType": "widget", "widgetType": "tabs",
        "settings": {"tabs": [{"tab_title": "Overview", "tab_content": "Details here"}]},
    }])

    sources = sorted(b.source for b in doc.blocks)
    assert sources == ["Details here", "Overview"]


def test_extracts_image_alt_text_only_not_url_or_id():
    doc = _doc([{
        "id": "img1", "elType": "widget", "widgetType": "image",
        "settings": {"image": {"url": "https://example.com/photo.jpg", "id": 42, "alt": "A field of crops"}},
    }])

    assert len(doc.blocks) == 1
    assert doc.blocks[0].source == "A field of crops"


def test_unknown_widget_type_is_left_untouched():
    doc = _doc([{"id": "x1", "elType": "widget", "widgetType": "some-exotic-widget", "settings": {"weird_field": "text"}}])

    assert doc.blocks == []


def test_apply_translations_updates_plain_field_and_preserves_everything_else():
    doc = _doc([{
        "id": "a1", "elType": "widget", "widgetType": "heading",
        "settings": {"title": "Precision Agriculture", "align": "center"},
    }])
    content_id = doc.blocks[0].content_id

    doc.apply_translations({content_id: "Agricultura de precisión"})
    result = json.loads(doc.to_json())

    assert result[0]["settings"]["title"] == "Agricultura de precisión"
    assert result[0]["settings"]["align"] == "center"
    assert result[0]["id"] == "a1"
    assert result[0]["widgetType"] == "heading"


def test_apply_translations_reassembles_html_field():
    doc = _doc([{
        "id": "te1", "elType": "widget", "widgetType": "text-editor",
        "settings": {"editor": "<p>Hello world.</p>"},
    }])
    content_id = doc.blocks[0].content_id

    doc.apply_translations({content_id: "Hola mundo."})
    result = json.loads(doc.to_json())

    assert result[0]["settings"]["editor"] == "<p>Hola mundo.</p>"


def test_apply_translations_updates_list_items_independently():
    doc = _doc([{
        "id": "il1", "elType": "widget", "widgetType": "icon-list",
        "settings": {"icon_list": [{"text": "First point"}, {"text": "Second point"}]},
    }])
    by_source = {b.source: b.content_id for b in doc.blocks}

    doc.apply_translations({
        by_source["First point"]: "Primer punto",
        by_source["Second point"]: "Segundo punto",
    })
    result = json.loads(doc.to_json())

    assert result[0]["settings"]["icon_list"][0]["text"] == "Primer punto"
    assert result[0]["settings"]["icon_list"][1]["text"] == "Segundo punto"


def test_apply_translations_updates_image_alt_preserving_url_and_id():
    doc = _doc([{
        "id": "img1", "elType": "widget", "widgetType": "image",
        "settings": {"image": {"url": "https://example.com/photo.jpg", "id": 42, "alt": "A field of crops"}},
    }])
    content_id = doc.blocks[0].content_id

    doc.apply_translations({content_id: "Un campo de cultivos"})
    result = json.loads(doc.to_json())

    assert result[0]["settings"]["image"]["alt"] == "Un campo de cultivos"
    assert result[0]["settings"]["image"]["url"] == "https://example.com/photo.jpg"
    assert result[0]["settings"]["image"]["id"] == 42


def test_apply_translations_ignores_content_ids_not_present():
    doc = _doc([{"id": "a1", "elType": "widget", "widgetType": "heading", "settings": {"title": "Original"}}])

    doc.apply_translations({"nonexistent_id": "Should not apply"})
    result = json.loads(doc.to_json())

    assert result[0]["settings"]["title"] == "Original"


def test_full_page_round_trip_preserves_structure_shape():
    original = [
        {
            "id": "sec1", "elType": "section", "settings": {"background_color": "#fff"},
            "elements": [
                {
                    "id": "col1", "elType": "column", "settings": {},
                    "elements": [
                        {"id": "h1", "elType": "widget", "widgetType": "heading", "settings": {"title": "Title"}},
                        {"id": "b1", "elType": "widget", "widgetType": "button", "settings": {"text": "Click"}},
                    ],
                }
            ],
        }
    ]
    doc = parse_elementor_document(json.dumps(original))
    translations = {b.content_id: b.source.upper() for b in doc.blocks}

    doc.apply_translations(translations)
    result = json.loads(doc.to_json())

    assert result[0]["id"] == "sec1"
    assert result[0]["settings"]["background_color"] == "#fff"
    assert result[0]["elements"][0]["elements"][0]["settings"]["title"] == "TITLE"
    assert result[0]["elements"][0]["elements"][1]["settings"]["text"] == "CLICK"
