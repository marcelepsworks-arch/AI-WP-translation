from app.qa.url_validator import check_urls, extract_urls


def test_extract_urls_finds_all_urls_in_text():
    text = "See https://www.precision-gnss.com/rtk-application/archaeology/ for details."

    assert extract_urls(text) == ["https://www.precision-gnss.com/rtk-application/archaeology/"]


def test_check_urls_passes_when_url_is_preserved():
    result = check_urls(
        'Learn more at https://www.ardusimple.com/products/simple-rtk2b/',
        'Más información en https://www.ardusimple.com/products/simple-rtk2b/',
    )

    assert result.passed is True
    assert result.missing_urls == []
    assert result.added_urls == []


def test_check_urls_flags_an_altered_url():
    result = check_urls(
        "Learn more at https://www.ardusimple.com/products/simple-rtk2b/",
        "Más información en https://www.ardusimple.com/products/simple-rtk3b/",
    )

    assert result.passed is False
    assert result.missing_urls == ["https://www.ardusimple.com/products/simple-rtk2b/"]
    assert result.added_urls == ["https://www.ardusimple.com/products/simple-rtk3b/"]


def test_check_urls_passes_when_no_urls_present_in_either_text():
    result = check_urls("Plain prose with no links.", "Prosa sin enlaces.")

    assert result.passed is True


def test_extract_urls_reads_href_attributes_structurally():
    html = '<a href="https://www.ardusimple.com/kits/">Basic Starter Kits</a>'

    assert extract_urls(html) == ["https://www.ardusimple.com/kits/"]


def test_check_urls_passes_when_only_the_link_text_is_translated():
    # Blocks arrive as raw inline HTML, so the anchor text sits right after
    # the href. Translating it must not read as an altered URL.
    result = check_urls(
        'Use 2x <a href="https://www.ardusimple.com/kits/">Basic Starter Kits</a> or the receiver.',
        'Usa 2x <a href="https://www.ardusimple.com/kits/">Kits Básicos</a> o el receptor.',
    )

    assert result.passed is True
    assert result.missing_urls == []
    assert result.added_urls == []


def test_check_urls_still_flags_an_altered_href():
    result = check_urls(
        '<a href="https://www.ardusimple.com/kits/">Starter Kits</a>',
        '<a href="https://www.ardusimple.com/other/">Kits Iniciales</a>',
    )

    assert result.passed is False
    assert result.missing_urls == ["https://www.ardusimple.com/kits/"]
    assert result.added_urls == ["https://www.ardusimple.com/other/"]
