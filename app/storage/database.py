"""SQLite schema and connection setup for the translation memory.

Table shapes match the project brief, section 18, exactly.
"""
from __future__ import annotations

import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS source_content (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    wp_post_id INTEGER NOT NULL,
    post_type TEXT NOT NULL,
    source_language TEXT NOT NULL,
    source_url TEXT,
    source_hash TEXT,
    last_seen TEXT,
    UNIQUE(wp_post_id, post_type)
);

CREATE TABLE IF NOT EXISTS content_blocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL REFERENCES source_content(id),
    block_id TEXT NOT NULL,
    block_type TEXT NOT NULL,
    source_text TEXT NOT NULL,
    source_hash TEXT NOT NULL,
    context TEXT,
    UNIQUE(source_id, block_id)
);

CREATE TABLE IF NOT EXISTS translations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_block_id INTEGER NOT NULL REFERENCES content_blocks(id),
    target_language TEXT NOT NULL,
    translated_text TEXT NOT NULL,
    translation_hash TEXT NOT NULL,
    model TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    status TEXT NOT NULL,
    confidence_score REAL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS terminology (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_term TEXT NOT NULL,
    target_term TEXT NOT NULL,
    language TEXT NOT NULL,
    context TEXT,
    rule_type TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS qa_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    translation_id INTEGER NOT NULL REFERENCES translations(id),
    check_type TEXT NOT NULL,
    status TEXT NOT NULL,
    score REAL,
    details TEXT
);
"""


def get_connection(db_path: str = ":memory:") -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn
