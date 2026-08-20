"""Cross-page translation memory.

Reuse used to be per page: `_gnss_block_hashes` is written onto the
translated post and `app.cli.sync` compares it block by block *within that
page*. A footer, CTA or legal notice repeated across forty pages was
therefore translated -- and paid for -- forty times.

The key is the exact source text plus the target language plus a
fingerprint of the configuration that produced the translation (see
`app.translation.fingerprint`). Context is deliberately excluded: including
the heading breadcrumb would mean the same footer under forty different
H1s never matches, and boilerplate is precisely where the budget goes.

Its own connection rather than `app.storage.database.get_connection`,
because blocks translate on a thread pool and a plain connection is not
shared across threads.
"""
from __future__ import annotations

import hashlib
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS translation_memory (
    source_hash TEXT NOT NULL,
    target_language TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    source_text TEXT NOT NULL,
    translated_text TEXT NOT NULL,
    hit_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    last_used_at TEXT NOT NULL,
    PRIMARY KEY (source_hash, target_language, fingerprint)
);
"""


def hash_source(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class TranslationMemory:
    def __init__(self, path: Path | str) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._conn.executescript(_SCHEMA)
            self._conn.commit()

    def lookup(self, source_text: str, target_language: str, fingerprint: str) -> str | None:
        """Returns a remembered translation, recording the hit. The caller is
        still expected to re-run the mechanical QA checks against it before
        using it -- this returns what was stored, not a promise it is still
        correct.
        """
        key = (hash_source(source_text), target_language, fingerprint)
        with self._lock:
            row = self._conn.execute(
                "SELECT translated_text FROM translation_memory"
                " WHERE source_hash = ? AND target_language = ? AND fingerprint = ?",
                key,
            ).fetchone()
            if row is None:
                return None
            self._conn.execute(
                "UPDATE translation_memory SET hit_count = hit_count + 1, last_used_at = ?"
                " WHERE source_hash = ? AND target_language = ? AND fingerprint = ?",
                (_now(), *key),
            )
            self._conn.commit()
        return row["translated_text"]

    def remember(self, source_text: str, translated_text: str, target_language: str, fingerprint: str) -> None:
        now = _now()
        with self._lock:
            self._conn.execute(
                "INSERT INTO translation_memory"
                " (source_hash, target_language, fingerprint, source_text, translated_text,"
                "  hit_count, created_at, last_used_at)"
                " VALUES (?, ?, ?, ?, ?, 0, ?, ?)"
                " ON CONFLICT(source_hash, target_language, fingerprint) DO UPDATE SET"
                "  translated_text = excluded.translated_text, last_used_at = excluded.last_used_at",
                (
                    hash_source(source_text), target_language, fingerprint,
                    source_text, translated_text, now, now,
                ),
            )
            self._conn.commit()

    def stats(self) -> dict:
        with self._lock:
            row = self._conn.execute(
                "SELECT COUNT(*) AS entries, COALESCE(SUM(hit_count), 0) AS hits FROM translation_memory"
            ).fetchone()
        return {"entries": row["entries"], "hits": row["hits"]}
