import pytest
from pydantic import ValidationError

from app.extraction.schemas import ContentBlock


def test_content_block_holds_all_required_fields():
    block = ContentBlock(
        content_id="page_4309_block_3",
        type="paragraph",
        context="RTK Applications > Precision Agriculture",
        source="RTK GNSS delivers 1 cm accuracy.",
        translate=True,
    )

    assert block.content_id == "page_4309_block_3"
    assert block.type == "paragraph"
    assert block.context == "RTK Applications > Precision Agriculture"
    assert block.source == "RTK GNSS delivers 1 cm accuracy."
    assert block.translate is True


def test_content_block_requires_content_id():
    with pytest.raises(ValidationError):
        ContentBlock(type="paragraph", context="", source="text", translate=True)
