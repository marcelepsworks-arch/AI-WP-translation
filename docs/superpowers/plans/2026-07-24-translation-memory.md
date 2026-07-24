# Translation Memory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete FASE 6 of `PLA-ACCIO.md`: a SQLite-backed translation memory that stores a content-hash fingerprint per block (brief section 18 schema) and detects, per block, whether it is new, changed, or unchanged since the last run — so re-translation only ever happens for content that actually changed (brief section 5).

**Architecture:** `app/storage/database.py` owns the SQLite schema and connection setup (`source_content`, `content_blocks`, `translations`, `terminology`, `qa_results` tables, matching the brief exactly). `app/storage/models.py` holds thin repository functions over a connection — no ORM, just parameterized SQL. `app/synchronization/change_detector.py` is pure logic: hash a block's text (SHA-256) and compare it against what is stored, returning `"new"` / `"changed"` / `"unchanged"` per block, consuming `ContentBlock` from `app.extraction.schemas` (FASE 3) directly — a real integration point between the two phases.

**Tech Stack:** Python 3.10 standard library only (`sqlite3`, `hashlib`) — no new dependency. `pytest` with an in-memory SQLite database (`:memory:`) per test — fast, no mocking needed since SQLite itself is the right level of fidelity here.

## Global Constraints

- Schema matches the brief (section 18) field-for-field: `source_content(id, wp_post_id, post_type, source_language, source_url, source_hash, last_seen)`, `content_blocks(id, source_id, block_id, block_type, source_text, source_hash, context)`, `translations(id, source_block_id, target_language, translated_text, translation_hash, model, prompt_version, status, confidence_score, created_at, updated_at)`, `terminology(id, source_term, target_term, language, context, rule_type)`, `qa_results(id, translation_id, check_type, status, score, details)`.
- Change detection must never mutate stored state as a side effect of detecting — `detect_changed_blocks()` is read-only; a separate `save_content_blocks()` call persists the new baseline once the caller has actually processed the changes.
- Code and comments in English.

---

## File Structure

```
app/storage/
├── __init__.py
└── database.py    # SCHEMA, get_connection()
app/storage/
└── models.py       # upsert_source_content(), save_content_blocks(), get_content_block_hash()

app/synchronization/
├── __init__.py
└── change_detector.py   # hash_text(), detect_changed_blocks()

tests/storage/
├── __init__.py
├── test_database.py
└── test_models.py
tests/synchronization/
├── __init__.py
└── test_change_detector.py
```

---

### Task 1: Database schema and connection

**Files:**
- Create: `app/storage/__init__.py`
- Create: `app/storage/database.py`
- Create: `tests/storage/__init__.py`
- Create: `tests/storage/test_database.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `get_connection(db_path: str = ":memory:") -> sqlite3.Connection`, with `conn.row_factory = sqlite3.Row`. Task 2 and Task 3 consume the connection.

- [ ] **Step 1: Create package init files**

`app/storage/__init__.py`:
```python
```

`tests/storage/__init__.py`:
```python
```

- [ ] **Step 2: Write the failing test — `tests/storage/test_database.py`**

```python
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
```

- [ ] **Step 3: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/storage/test_database.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.storage.database'`.

- [ ] **Step 4: Write minimal implementation — `app/storage/database.py`**

```python
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
```

- [ ] **Step 5: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/storage/test_database.py -v`
Expected: 3 passed.

- [ ] **Step 6: Commit and push**

```bash
git add app/storage/__init__.py app/storage/database.py tests/storage/__init__.py tests/storage/test_database.py
git commit -m "feat: add SQLite translation memory schema (brief section 18)"
git push origin master
```

---

### Task 2: Repository functions

**Files:**
- Create: `app/storage/models.py`
- Create: `tests/storage/test_models.py`

**Interfaces:**
- Consumes: `get_connection()` (Task 1).
- Produces: `upsert_source_content(conn, wp_post_id: int, post_type: str, source_language: str, source_url: str = "", source_hash: str = "") -> int` (returns `source_content.id`); `save_content_block(conn, source_id: int, block_id: str, block_type: str, source_text: str, source_hash: str, context: str = "") -> None`; `get_content_block_hash(conn, source_id: int, block_id: str) -> str | None`. Task 4 (`change_detector.py`) calls `get_content_block_hash`; a future FASE 8 orchestrator calls `upsert_source_content`/`save_content_block`.

- [ ] **Step 1: Write the failing test — `tests/storage/test_models.py`**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/storage/test_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.storage.models'`.

- [ ] **Step 3: Write minimal implementation — `app/storage/models.py`**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/storage/test_models.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit and push**

```bash
git add app/storage/models.py tests/storage/test_models.py
git commit -m "feat: add translation memory repository functions"
git push origin master
```

---

### Task 3: Change detection

**Files:**
- Create: `app/synchronization/__init__.py`
- Create: `app/synchronization/change_detector.py`
- Create: `tests/synchronization/__init__.py`
- Create: `tests/synchronization/test_change_detector.py`

**Interfaces:**
- Consumes: `get_content_block_hash()` (Task 2), `ContentBlock` (from `app.extraction.schemas`, FASE 3).
- Produces: `hash_text(text: str) -> str`; `detect_changed_blocks(conn, source_id: int, blocks: list[ContentBlock]) -> dict[str, str]` (maps `content_id` to `"new"` / `"changed"` / `"unchanged"`).

- [ ] **Step 1: Create package init files**

`app/synchronization/__init__.py`:
```python
```

`tests/synchronization/__init__.py`:
```python
```

- [ ] **Step 2: Write the failing test — `tests/synchronization/test_change_detector.py`**

```python
from app.extraction.schemas import ContentBlock
from app.storage.database import get_connection
from app.storage.models import save_content_block, upsert_source_content
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

    from app.storage.models import get_content_block_hash
    assert get_content_block_hash(conn, source_id, "b1") == hash_text("Original.")
```

- [ ] **Step 3: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/synchronization/test_change_detector.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.synchronization.change_detector'`.

- [ ] **Step 4: Write minimal implementation — `app/synchronization/change_detector.py`**

```python
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
```

- [ ] **Step 5: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/synchronization/test_change_detector.py -v`
Expected: 6 passed.

- [ ] **Step 6: Run the full project test suite**

Run: `.venv/Scripts/python.exe -m pytest -v`
Expected: all tests pass (103 existing + 3 + 5 + 6 = 117 total).

- [ ] **Step 7: Commit and push**

```bash
git add app/synchronization/__init__.py app/synchronization/change_detector.py tests/synchronization/__init__.py tests/synchronization/test_change_detector.py
git commit -m "feat: add change detection (new/changed/unchanged) for content blocks"
git push origin master
```

---

### Task 4: Update tracking docs

**Files:**
- Modify: `PLA-ACCIO.md`
- Modify: `LOG.md`

- [ ] **Step 1:** Mark `PLA-ACCIO.md` FASE 6.1, 6.2, 6.4 as done; note 6.3 (WPML `md5`/`needs_update` cross-check) as still blocked on `gnss-bridge`/WPML.
- [ ] **Step 2:** Add a `LOG.md` entry.
- [ ] **Step 3: Commit and push**

```bash
git add PLA-ACCIO.md LOG.md docs/superpowers/plans/2026-07-24-translation-memory.md
git commit -m "docs: mark FASE 6.1/6.2/6.4 done, log translation memory session"
git push origin master
```

---

## Out of scope for this plan

- FASE 6.3 (cross-checking against WPML's `icl_translation_status.md5`/`needs_update`) — blocked on `gnss-bridge` (FASE 1) and WPML itself.
- `translations`/`qa_results` table writes — no code writes to those tables yet; that happens once FASE 8 orchestration exists to actually call `DeepSeekClient` and persist results.
