from app.qa.html_structure_checker import check_html_structure


def test_plain_text_on_both_sides_passes():
    result = check_html_structure("Plain prose, no markup.", "Prosa sin marcado.")

    assert result.passed is True
    assert result.repaired is False
    assert result.tag_skeleton_matches is True


def test_inline_link_translated_normally_passes():
    source = 'Use the <a href="https://example.com/kits">Basic Starter Kits</a> today.'
    translated = 'Usa los <a href="https://example.com/kits">Kits Básicos</a> hoy.'

    result = check_html_structure(source, translated)

    assert result.passed is True
    assert result.repaired is False


def test_lost_space_before_inline_tag_is_detected_and_repaired():
    # The exact failure mode none of the four original QA signals could see:
    # the number, the terminology, the URL and the meaning are all intact,
    # only the space before <a> is gone -- rendering as "2xBasic Starter Kits".
    source = 'With this you can use 2x <a href="https://example.com/kits">Basic Starter Kits</a> or the receiver.'
    translated = 'Con esto puedes utilizar 2x<a href="https://example.com/kits">Kits Básicos</a> o el receptor.'

    result = check_html_structure(source, translated)

    assert result.tag_skeleton_matches is True
    assert result.repaired is True
    assert result.passed is True
    assert "2x <a" in result.repaired_translation
    assert result.glued_boundaries == ["before <a>"]


def test_lost_space_after_closing_tag_is_repaired():
    source = "Read the <strong>warning</strong> before installing."
    translated = "Lee la <strong>advertencia</strong>antes de instalar."

    result = check_html_structure(source, translated)

    assert result.repaired is True
    assert "</strong> antes" in result.repaired_translation
    assert result.glued_boundaries == ["after </strong>"]


def test_dropped_tag_fails_and_is_not_repaired():
    source = 'See the <a href="https://example.com/docs">manual</a> for details.'
    translated = "Consulta el manual para más detalles."

    result = check_html_structure(source, translated)

    assert result.tag_skeleton_matches is False
    assert result.passed is False
    assert result.repaired is False
    assert result.repaired_translation == translated


def test_altered_href_fails():
    source = '<a href="https://example.com/a">link</a>'
    translated = '<a href="https://example.com/b">enlace</a>'

    result = check_html_structure(source, translated)

    assert result.tag_skeleton_matches is False
    assert result.passed is False


def test_added_tag_fails():
    source = "A plain sentence."
    translated = "Una frase <strong>simple</strong>."

    result = check_html_structure(source, translated)

    assert result.tag_skeleton_matches is False
    assert result.passed is False


def test_source_attribute_stripped_by_the_sanitizer_is_not_a_false_failure():
    # The source keeps class="x" (it is never sanitized), while the translation
    # has already been through sanitize_html(), which drops it. Comparing the
    # two raw would flag every styled span as a structural failure.
    source = '<span class="highlight">Warning</span> follows.'
    translated = "<span>Advertencia</span> a continuación."

    result = check_html_structure(source, translated)

    assert result.tag_skeleton_matches is True
    assert result.passed is True


def test_single_quoted_source_attributes_are_not_a_false_failure():
    source = "<a href='https://example.com'>link</a>"
    translated = '<a href="https://example.com">enlace</a>'

    result = check_html_structure(source, translated)

    assert result.passed is True


def test_added_space_is_not_flagged():
    # Only losing a space glues words together; gaining one is harmless and
    # happens legitimately when a translation reorders around a tag.
    source = "Use<strong>this</strong>now."
    translated = "Usa <strong>esto</strong> ahora."

    result = check_html_structure(source, translated)

    assert result.passed is True
    assert result.repaired is False


def test_tag_moved_to_the_start_by_reordering_is_not_flagged():
    # Spanish reorders the anchor to the front, so the space that preceded it
    # in the source is now the start of the string -- not a glued boundary.
    source = 'You can use 2x <a href="https://example.com/k">Starter Kits</a>.'
    translated = '<a href="https://example.com/k">Kits Iniciales</a> x2 disponibles.'

    result = check_html_structure(source, translated)

    assert result.passed is True
    assert result.repaired is False


def test_multiple_glued_boundaries_are_all_repaired():
    source = "Get <strong>this</strong> and <em>that</em> now."
    translated = "Consigue<strong>esto</strong> y<em>aquello</em> ahora."

    result = check_html_structure(source, translated)

    assert result.repaired is True
    assert result.glued_boundaries == ["before <strong>", "before <em>"]
    assert "Consigue <strong>" in result.repaired_translation
    assert "y <em>" in result.repaired_translation
