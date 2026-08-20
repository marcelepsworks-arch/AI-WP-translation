# Translation memory and Elementor snippet coverage — design

Date: 2026-08-20
Status: approved in chat, pending implementation

## Problem

Three defects, found while auditing why a lost space around an inline
`<a>` tag was auto-approved with a perfect QA score.

1. **(Delivered)** No QA signal watched the inline HTML skeleton of a
   block. A translation that glued text to a tag (`2x<a href=...>`)
   scored 100 and auto-approved, because the number, the terminology,
   the URL and the meaning were all intact.
2. **No cross-page reuse.** Reuse is per page only: `_gnss_block_hashes`
   is stored on the translated post and `app.cli.sync` compares it
   block-by-block within that page. Boilerplate repeated across 40 pages
   is translated and paid for 40 times. The SQLite schema in
   `app/storage/database.py` is documented as "translation memory" but
   is unreachable from the runtime — neither `app.cli.translate` nor
   `app.cli.sync` imports `app.storage`.
3. **Elementor `html` widgets are never translated.** The widget type is
   absent from every allowlist in `app/extraction/elementor_extractor.py`,
   and on an Elementor page `app.cli.translate` passes `skip_body=True`,
   discarding the rendered body. A snippet inside an Elementor HTML
   widget is therefore invisible from both directions at once.

## Evidence

Probe against `https://staging5.ardusimple.com/compatible-software/`,
2026-08-20, unauthenticated:

- The page **is** an Elementor page: 10 `elementor-widget` markers, one
  `data-elementor-type` root. What reads as "a JavaScript page" is an
  Elementor HTML widget holding a WordPress snippet.
- `extract_blocks()` finds **2 blocks** on the entire page.
- Six UI labels (`Platform:`, `All Platforms`, `Android`, `iOS`,
  `Windows`, `Category:`) sit in `<div class="filter-label">` and
  `<label class="filter-option">` — outside the extractor's selector.
- The catalogue is **not in WordPress**. The widget's 12.7 KB of inline
  JS is a renderer that does
  `await fetch('.../uploads/2026/02/compatible-software.csv')`.
  That CSV is 66 rows x 10 columns.
  Translatable columns: `Category`, `Description`, `Price/Trial`.
  Never translate: `App Name`, `Developer`, `Tutorial Link`, `Icon URL`,
  `App URL`, `Platform`, `Recommended`.

Consequence: nobody needs to separate code from prose inside
JavaScript — the hard, unsolvable-in-general problem. The content is a
structured table whose header names the prose columns.

## Constraints

- **Elementor compatibility is non-negotiable.** The large majority of
  pages are Elementor. No change may regress that path.
- **The CSV is untouchable.** It stays a single English file that the
  team edits exactly as today. No extra columns, no sibling files, no
  new authoring step for anyone.

## Open question (blocks nothing)

Whether `_elementor_data` is actually exposed over REST could not be
verified: the bridge plugin registers it behind
`auth_callback => gnss_bridge_permission_check`, and `.env` holds a
production application password but none for staging. It decides whether
section B or section C does the work on a given site; both are needed
regardless, so implementation proceeds.

Also noted: `.env` targets `staging.precision-gnss.com`, a different
site from the `staging5.ardusimple.com` used for the probe.

## Section A — Translation memory

A new table, because the existing `translations` table keys off
`content_blocks(id)`, which is per page — the very thing being escaped.

```sql
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
```

**Key semantics (decided):** exact source text, ignoring context. Context
is deliberately excluded — including it would mean the same footer under
40 different H1s never matches, and boilerplate is exactly where the
budget burns.

**Fingerprint** does not exist today and must be introduced:
`sha256(PROMPT_VERSION + glossary_hash + model)`. Without it, editing the
prompt would leave the memory serving the previous generation forever.

**Reuse protocol (decided):** on a hit, skip both AI calls — those are
what costs money — then re-run all four mechanical checks (numbers,
terminology, URLs, structure) against the recovered pair. If any fails,
do not reuse: translate fresh and overwrite the entry. Only blocks that
scored `auto_approve` are ever memorised.

**Provenance:** `BlockResult` gains `from_memory: bool`. It belongs there
and not on `QAReport`, which carries quality signals, not origin. A
reused translation inherits `review_passed=True` from the original run —
legitimate, since source text and fingerprint are byte-identical — but
that inheritance must be visible rather than implied.

**Concurrency:** `translate_blocks` runs a `ThreadPoolExecutor`. SQLite
needs a connection per thread or an explicit lock; otherwise the failure
is intermittent corruption that is painful to diagnose.

## Section B — Elementor `html` widget

The widget must **not** be added to `_HTML_FIELDS` alongside
`text-editor`. `extract_blocks()` decomposes `<script>`
(`html_parser.py`), so the reassembly would emit the widget stripped of
its JavaScript — silent corruption of precisely the widget type this
work exists to support, and a direct violation of the Elementor
constraint.

It gets a dedicated handler instead: extract translatable text from the
non-script portion, preserve every `<script>` byte for byte, never send
script content to the translator.

Guarantee test: a widget with no translatable text round-trips
byte-identical.

## Section C — Selector widening

Add `td`, `th`, `dt`, `dd`, `figcaption`, `caption`, `label`, `summary`,
and `div`/`span` **only when they carry their own direct text**. On the
probed page that heuristic yields 4 divs rather than hundreds.

Elementor pages are largely insulated because they take the
`skip_body=True` path — but only where `_elementor_data` is genuinely
exposed, which is the open question above. The `_is_inside_text_block`
guard must be extended so a cell containing a `<p>` is not extracted
twice.

## Section D — Catalogue endpoint

A new REST route on the gnss-bridge plugin reads the original CSV,
applies a translation map uploaded by the pipeline, and returns a CSV of
identical shape. The pipeline rewrites the `fetch()` URL only inside the
translated copy of the widget; the English page and the English CSV are
never touched.

**Security:** the parameter naming the source CSV must be validated —
same origin, under `/uploads/`, `.csv` extension. Unvalidated, it is an
SSRF against the site's own network.

Repeated cell values (`Free`, `Free Trial`, category names) flow through
the section A memory, so they are paid for once across all 66 rows.

## Order

1. Verify `_elementor_data` exposure with staging credentials. *(Blocked:
   no staging application password.)*
2. Section B — `html` widget handler with script preservation.
3. Section C — selector widening.
4. Section A — translation memory.
5. Section D — catalogue endpoint and URL rewrite.
