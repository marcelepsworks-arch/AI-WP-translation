"""Repository functions over the translation-memory SQLite schema.
Plain parameterized SQL — no ORM.
"""
from __future__ import annotations

import sqlite3


def upsert_source_content(
    conn: sqlite3.Connection,
    wp_post_id: int,
    post_type: str,
    source_language: str,
    source_url: str = "",
    source_hash: str = "",
) -> int:
    conn.execute(
        """
        INSERT INTO source_content (wp_post_id, post_type, source_language, source_url, source_hash)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(wp_post_id, post_type) DO UPDATE SET
            source_language = excluded.source_language,
            source_url = excluded.source_url,
            source_hash = excluded.source_hash
        """,
        (wp_post_id, post_type, source_language, source_url, source_hash),
    )
    conn.commit()
    row = conn.execute(
        "SELECT id FROM source_content WHERE wp_post_id = ? AND post_type = ?",
        (wp_post_id, post_type),
    ).fetchone()
    return row["id"]


def save_content_block(
    conn: sqlite3.Connection,
    source_id: int,
    block_id: str,
    block_type: str,
    source_text: str,
    source_hash: str,
    context: str = "",
) -> None:
    conn.execute(
        """
        INSERT INTO content_blocks (source_id, block_id, block_type, source_text, source_hash, context)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(source_id, block_id) DO UPDATE SET
            block_type = excluded.block_type,
            source_text = excluded.source_text,
            source_hash = excluded.source_hash,
            context = excluded.context
        """,
        (source_id, block_id, block_type, source_text, source_hash, context),
    )
    conn.commit()


def get_content_block_hash(conn: sqlite3.Connection, source_id: int, block_id: str) -> str | None:
    row = conn.execute(
        "SELECT source_hash FROM content_blocks WHERE source_id = ? AND block_id = ?",
        (source_id, block_id),
    ).fetchone()
    return row["source_hash"] if row else None
