import pytest

from app.extraction.protected_content import is_protected_content


@pytest.mark.parametrize(
    "text",
    [
        "https://www.precision-gnss.com/rtk-application/archaeology/",
        "http://example.com",
        "www.ardusimple.com",
        "support@precision-gnss.com",
        "[contact-form-7 id=\"123\"]",
        "",
        "   ",
    ],
)
def test_is_protected_content_flags_urls_emails_shortcodes_and_empty_text(text):
    assert is_protected_content(text) is True


@pytest.mark.parametrize(
    "text",
    [
        "The ZED-F9P module delivers 1 cm RTK accuracy.",
        "Learn more",
        "Contact us at our office for more information.",
        "Base station setup takes about 8 seconds.",
    ],
)
def test_is_protected_content_does_not_flag_normal_prose(text):
    assert is_protected_content(text) is False


def test_is_protected_content_flags_url_even_with_surrounding_whitespace():
    assert is_protected_content("  https://example.com/page/  ") is True
