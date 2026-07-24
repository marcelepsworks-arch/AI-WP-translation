"""Detects whether each extracted content block is new, changed, or
unchanged since the last time it was seen — so only content that
actually changed gets re-translated (brief section 5).

Read-only: never writes to the translation memory. A caller decides
when to persist the new baseline via app.storage.models.save_content_block.
"""
from __future__ import annotations

import hashlib
import sqlite3

from app.extraction.schemas import ContentBlock
from app.storage.models import get_content_block_hash


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def detect_changed_blocks(
    conn: sqlite3.Connection,
    source_id: int,
    blocks: list[ContentBlock],
) -> dict[str, str]:
    result: dict[str, str] = {}

    for block in blocks:
        stored_hash = get_content_block_hash(conn, source_id, block.content_id)
        current_hash = hash_text(block.source)

        if stored_hash is None:
            result[block.content_id] = "new"
        elif stored_hash != current_hash:
            result[block.content_id] = "changed"
        else:
            result[block.content_id] = "unchanged"

    return result
