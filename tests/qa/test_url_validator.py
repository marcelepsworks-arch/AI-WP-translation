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
