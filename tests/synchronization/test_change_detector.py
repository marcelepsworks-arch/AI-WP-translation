from app.extraction.schemas import ContentBlock
from app.storage.database import get_connection
from app.storage.models import get_content_block_hash, save_content_block, upsert_source_content
from app.synchronization.change_detector import detect_changed_blocks, hash_text


def _block(content_id: str, source: str) -> ContentBlock:
    return ContentBlock(content_id=content_id, type="paragraph", context="Intro", source=source, translate=True)


def test_hash_text_is_deterministic():
    assert hash_text("RTK delivers 1 cm accuracy.") == hash_text("RTK delivers 1 cm accuracy.")


def test_hash_text_differs_for_different_text():
    assert hash_text("Version one.") != hash_text("Version two.")


def test_detect_changed_blocks_marks_all_as_new_when_source_has_no_prior_blocks():
    conn = get_connection(":memory:")
    source_id = upsert_source_content(conn, wp_post_id=1, post_type="page", source_language="en")
    blocks = [_block("b1", "First paragraph."), _block("b2", "Second paragraph.")]

    result = detect_changed_blocks(conn, source_id, blocks)

    assert result == {"b1": "new", "b2": "new"}


def test_detect_changed_blocks_marks_unchanged_when_hash_matches_stored_value():
    conn = get_connection(":memory:")
    source_id = upsert_source_content(conn, wp_post_id=1, post_type="page", source_language="en")
    text = "RTK delivers 1 cm accuracy."
    save_content_block(conn, source_id, "b1", "paragraph", text, hash_text(text))

    result = detect_changed_blocks(conn, source_id, [_block("b1", text)])

    assert result == {"b1": "unchanged"}


def test_detect_changed_blocks_marks_changed_when_only_one_paragraph_edited():
    conn = get_connection(":memory:")
    source_id = upsert_source_content(conn, wp_post_id=1, post_type="page", source_language="en")
    save_content_block(conn, source_id, "b1", "paragraph", "First paragraph.", hash_text("First paragraph."))
    save_content_block(conn, source_id, "b2", "paragraph", "Second paragraph.", hash_text("Second paragraph."))

    updated_blocks = [
        _block("b1", "First paragraph."),  # unchanged
        _block("b2", "Second paragraph, now edited."),  # changed
    ]
    result = detect_changed_blocks(conn, source_id, updated_blocks)

    assert result == {"b1": "unchanged", "b2": "changed"}


def test_detect_changed_blocks_does_not_mutate_stored_state():
    conn = get_connection(":memory:")
    source_id = upsert_source_content(conn, wp_post_id=1, post_type="page", source_language="en")
    save_content_block(conn, source_id, "b1", "paragraph", "Original.", hash_text("Original."))

    detect_changed_blocks(conn, source_id, [_block("b1", "Changed text.")])

    assert get_content_block_hash(conn, source_id, "b1") == hash_text("Original.")
