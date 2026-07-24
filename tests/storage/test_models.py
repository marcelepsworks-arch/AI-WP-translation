from app.storage.database import get_connection
from app.storage.models import (
    get_content_block_hash,
    save_content_block,
    upsert_source_content,
)


def test_upsert_source_content_inserts_and_returns_id():
    conn = get_connection(":memory:")

    source_id = upsert_source_content(
        conn, wp_post_id=4309, post_type="page", source_language="en",
        source_url="https://staging.precision-gnss.com/precision-agriculture/",
        source_hash="abc123",
    )

    row = conn.execute("SELECT * FROM source_content WHERE id = ?", (source_id,)).fetchone()
    assert row["wp_post_id"] == 4309
    assert row["source_hash"] == "abc123"


def test_upsert_source_content_updates_existing_row_on_second_call():
    conn = get_connection(":memory:")

    first_id = upsert_source_content(conn, wp_post_id=4309, post_type="page", source_language="en", source_hash="hash1")
    second_id = upsert_source_content(conn, wp_post_id=4309, post_type="page", source_language="en", source_hash="hash2")

    assert first_id == second_id
    row = conn.execute("SELECT * FROM source_content WHERE id = ?", (first_id,)).fetchone()
    assert row["source_hash"] == "hash2"


def test_save_content_block_then_get_content_block_hash_round_trips():
    conn = get_connection(":memory:")
    source_id = upsert_source_content(conn, wp_post_id=1, post_type="page", source_language="en")

    save_content_block(
        conn, source_id=source_id, block_id="block_1", block_type="paragraph",
        source_text="RTK delivers 1 cm accuracy.", source_hash="hash-a", context="Intro",
    )

    result = get_content_block_hash(conn, source_id=source_id, block_id="block_1")
    assert result == "hash-a"


def test_get_content_block_hash_returns_none_when_block_not_seen_before():
    conn = get_connection(":memory:")
    source_id = upsert_source_content(conn, wp_post_id=1, post_type="page", source_language="en")

    result = get_content_block_hash(conn, source_id=source_id, block_id="unknown_block")

    assert result is None


def test_save_content_block_updates_hash_on_second_call_with_same_block_id():
    conn = get_connection(":memory:")
    source_id = upsert_source_content(conn, wp_post_id=1, post_type="page", source_language="en")

    save_content_block(conn, source_id=source_id, block_id="block_1", block_type="paragraph", source_text="v1", source_hash="hash-v1")
    save_content_block(conn, source_id=source_id, block_id="block_1", block_type="paragraph", source_text="v2", source_hash="hash-v2")

    result = get_content_block_hash(conn, source_id=source_id, block_id="block_1")
    assert result == "hash-v2"
