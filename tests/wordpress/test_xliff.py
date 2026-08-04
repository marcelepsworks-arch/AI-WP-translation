import xml.etree.ElementTree as ET

from app.wordpress.xliff import build_translated_xliff, parse_xliff

NAMESPACED_XLIFF = """<?xml version="1.0" encoding="UTF-8"?>
<xliff version="1.2" xmlns="urn:oasis:names:tc:xliff:document:1.2">
  <file original="post-42" source-language="en" target-language="es" datatype="plaintext">
    <body>
      <trans-unit id="1" resname="title">
        <source>RTK GNSS for Robotics</source>
      </trans-unit>
      <trans-unit id="2">
        <source>The base station broadcasts corrections.</source>
      </trans-unit>
      <trans-unit id="3">
        <source></source>
      </trans-unit>
    </body>
  </file>
</xliff>
"""

UNNAMESPACED_XLIFF = """<?xml version="1.0" encoding="UTF-8"?>
<xliff version="1.2">
  <file original="post-42" source-language="en" target-language="es" datatype="plaintext">
    <body>
      <trans-unit id="1">
        <source>Rover connects via NTRIP.</source>
      </trans-unit>
    </body>
  </file>
</xliff>
"""


def _local_names(element: ET.Element) -> list[str]:
    return [child.tag.rsplit("}", 1)[-1] for child in element]


def test_parse_xliff_extracts_content_blocks():
    blocks = parse_xliff(NAMESPACED_XLIFF)

    assert len(blocks) == 2
    assert blocks[0].content_id == "1"
    assert blocks[0].type == "xliff_segment"
    assert blocks[0].context == "title"
    assert blocks[0].source == "RTK GNSS for Robotics"
    assert blocks[0].translate is True


def test_parse_xliff_uses_empty_context_when_no_resname():
    blocks = parse_xliff(NAMESPACED_XLIFF)

    assert blocks[1].content_id == "2"
    assert blocks[1].context == ""


def test_parse_xliff_skips_trans_units_with_empty_source():
    blocks = parse_xliff(NAMESPACED_XLIFF)

    assert "3" not in [block.content_id for block in blocks]


def test_parse_xliff_tolerates_missing_namespace():
    blocks = parse_xliff(UNNAMESPACED_XLIFF)

    assert len(blocks) == 1
    assert blocks[0].source == "Rover connects via NTRIP."


def test_build_translated_xliff_inserts_target_after_source():
    result = build_translated_xliff(
        NAMESPACED_XLIFF,
        {"1": "RTK GNSS para Robótica", "2": "La estación base transmite correcciones."},
    )

    root = ET.fromstring(result)
    trans_units = [el for el in root.iter() if el.tag.rsplit("}", 1)[-1] == "trans-unit"]

    unit_1 = next(u for u in trans_units if u.get("id") == "1")
    assert _local_names(unit_1) == ["source", "target"]
    target = next(c for c in unit_1 if c.tag.rsplit("}", 1)[-1] == "target")
    assert target.text == "RTK GNSS para Robótica"


def test_build_translated_xliff_leaves_untranslated_units_unchanged():
    result = build_translated_xliff(NAMESPACED_XLIFF, {"1": "RTK GNSS para Robótica"})

    root = ET.fromstring(result)
    trans_units = [el for el in root.iter() if el.tag.rsplit("}", 1)[-1] == "trans-unit"]

    unit_2 = next(u for u in trans_units if u.get("id") == "2")
    assert "target" not in _local_names(unit_2)


def test_build_translated_xliff_updates_existing_target_without_duplicating():
    already_translated = NAMESPACED_XLIFF.replace(
        "<source>RTK GNSS for Robotics</source>",
        "<source>RTK GNSS for Robotics</source><target>old translation</target>",
    )

    result = build_translated_xliff(already_translated, {"1": "RTK GNSS para Robótica (revisado)"})

    root = ET.fromstring(result)
    trans_units = [el for el in root.iter() if el.tag.rsplit("}", 1)[-1] == "trans-unit"]
    unit_1 = next(u for u in trans_units if u.get("id") == "1")
    targets = [c for c in unit_1 if c.tag.rsplit("}", 1)[-1] == "target"]

    assert len(targets) == 1
    assert targets[0].text == "RTK GNSS para Robótica (revisado)"


def test_build_translated_xliff_works_without_namespace():
    result = build_translated_xliff(UNNAMESPACED_XLIFF, {"1": "El rover se conecta vía NTRIP."})

    root = ET.fromstring(result)
    trans_unit = next(el for el in root.iter() if el.tag.rsplit("}", 1)[-1] == "trans-unit")
    target = next(c for c in trans_unit if c.tag.rsplit("}", 1)[-1] == "target")

    assert target.text == "El rover se conecta vía NTRIP."
