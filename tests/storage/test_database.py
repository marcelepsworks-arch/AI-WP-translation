from app.storage.database import get_connection

_EXPECTED_TABLES = {
    "source_content",
    "content_blocks",
    "translations",
    "terminology",
    "qa_results",
}


def test_get_connection_creates_all_expected_tables():
    conn = get_connection(":memory:")

    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    table_names = {row["name"] for row in rows}

    assert _EXPECTED_TABLES.issubset(table_names)


def test_get_connection_uses_row_factory_for_dict_like_access():
    conn = get_connection(":memory:")

    conn.execute(
        "INSERT INTO source_content (wp_post_id, post_type, source_language) VALUES (?, ?, ?)",
        (4309, "page", "en"),
    )
    row = conn.execute("SELECT * FROM source_content").fetchone()

    assert row["wp_post_id"] == 4309
    assert row["post_type"] == "page"


def test_get_connection_is_idempotent_when_called_twice_on_same_file(tmp_path):
    db_path = str(tmp_path / "test.db")

    conn1 = get_connection(db_path)
    conn1.close()
    conn2 = get_connection(db_path)  # must not raise on existing tables

    rows = conn2.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    assert {row["name"] for row in rows}.issuperset(_EXPECTED_TABLES)
