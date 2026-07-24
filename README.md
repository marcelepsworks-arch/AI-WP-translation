# GNSS AI Translation Engine

**Automated, technically-accurate English → Spanish translation for [Precision-GNSS.com](https://www.precision-gnss.com), a GNSS/RTK technical knowledge platform.**

A dedicated translation service that sits between WordPress and an AI model — never a script that pipes text through an LLM and republishes whatever comes back. Every translation is written, independently reviewed, and terminology-checked before a human ever sees it, and nothing is ever auto-published.

---

## Philosophy

Generic machine translation optimizes for text that *reads well*. This project optimizes for something else first: that the Spanish version says **exactly** the same thing as the English original — the same numbers, the same units, the same conditions, the same degree of certainty.

That distinction matters because the content is technical: RTK accuracy figures, correction-service ranges, product specifications, safety notes. A fluent-sounding mistranslation that quietly turns "1 cm accuracy" into "2 cm accuracy," or "within 5 seconds" into "in under 5 seconds," is a worse outcome than an awkward but correct sentence. So the system is built around **independent verification**, not a single AI call trusted to get everything right at once.

This isn't theoretical. During development, the Translator alone mistranslated *"achieves a fix within 5 seconds"* (i.e. in **at most** 5 seconds) as *"en menos de 5 segundos"* (in **strictly less than** 5 seconds) — a real, subtle technical drift. The independent Reviewer step caught it and correctly rejected the translation. A single combined request would very likely have missed it.

---

## How It Works

```mermaid
flowchart LR
    WP["WordPress\nPrecision-GNSS.com\nWPML + Elementor + Yoast"] -->|REST API| Bridge["gnss-bridge\nlightweight mu-plugin\n(designed, not yet deployed)"]
    Bridge --> Engine["Translation Engine\nPython service"]
    Engine --> DS["DeepSeek API"]
```

The `gnss-bridge` component exists because WPML does not expose a public REST API for creating or linking translations — that's only possible through internal PHP hooks that must run inside WordPress itself. A minimal, auditable bridge plugin is the safest way to reach those hooks, instead of writing directly to WPML's database tables, which WPML's own documentation advises against.

### The translation pipeline

```mermaid
flowchart LR
    Source["Source text\n+ context"] --> T["1. Translator\nDeepSeek call\n+ glossary subset"]
    T --> R["2. Technical Reviewer\ncompares source vs.\ntranslation"]
    R --> V["3. Terminology Validator\naudits mandatory\nglossary terms"]
    V --> Decision{QA score}
    Decision -->|"≥ 95"| Approve["Draft, ready\nfor human review"]
    Decision -->|"85-94"| Review["Flagged for\nhuman review"]
    Decision -->|"< 85"| Reject["Rejected"]
```

Translation and quality-checking are three **independent** AI calls, never one combined request:

1. **Translator** — writes the Spanish translation under a strict system prompt (15 mandatory rules + 6 explicit prohibitions): preserve exact meaning, numbers, units, conditions, warnings, certainty; never simplify, invent, soften, or drop technical information; never translate protected product names or acronyms without instruction.
2. **Technical Reviewer** — independently compares source and translation, hunting specifically for information added, removed, or subtly altered.
3. **Terminology Validator** — audits the translation against the domain glossary, flagging any deviation from required vocabulary (e.g. *"base station" → "estación base"*).

Each call returns strict, validated JSON (Pydantic schemas) — never free text — so results are auditable and machine-checkable, not just "trust the model."

---

## Design

Three concerns are kept deliberately apart: **WordPress never talks to DeepSeek directly, and DeepSeek has no awareness of WordPress.** An independent Python service owns all the intelligence — extraction rules, glossary logic, change detection, quality gates — and is the only thing that talks to either side.

| Decision | Why |
|---|---|
| Translation logic lives in an external Python service, not a WordPress plugin | Three sequential AI calls per block can take several seconds. Doing that inside a PHP request risks timeouts on shared hosting and has no real retry/queue story. |
| A minimal `gnss-bridge` mu-plugin bridges WPML | WPML's translation-linking hooks are PHP-only, reachable only from inside WordPress — but writing straight into WPML's database tables is explicitly unsafe per WPML's own docs. |
| Extraction works off rendered HTML, not raw Elementor JSON | `_elementor_data` isn't exposed via the REST API on this site. Elementor's own rendered output is plain HTML — headings, paragraphs, lists, buttons — and is available today. |
| Change detection is a pure, read-only function | `detect_changed_blocks()` never mutates state as a side effect of checking it — a caller decides when to persist a new baseline, after the content has actually been translated. |
| QA scoring combines 4 measurable signals, not 5 abstract dimensions | Rather than inventing scores for categories with no real data to calibrate against, the score combines what can actually be checked mechanically: numbers, protected terms, URLs, and the Reviewer's verdict. |
| Nothing is ever auto-published | Every translation lands as a draft. A human always has the final say before it goes live. |

---

## Cost

Figures below are **measured, not estimated** — computed by scraping real Precision-GNSS.com pages and running them through the project's actual `chunk_text()` splitter and real system-prompt sizes, using DeepSeek's published pricing (`deepseek-v4-pro`: $0.435 / $0.87 per 1M input/output tokens).

| Metric | Value |
|---|---|
| Average cost per page — translation only | **$0.0064** |
| Average cost per page — with full independent review | **$0.0129** |
| Cost per 1,000 characters — full pipeline | **$0.00085** (remarkably flat across every page tested) |

**In practical terms:** translating and fully reviewing a typical content page costs about one-hundredth of a dollar. A full first pass across 50 comparable pages costs roughly **$0.64** total. Ongoing cost after launch is far lower still, since the translation memory only re-translates blocks that actually changed — never a whole page for a one-paragraph edit.

Using the cheaper `deepseek-v4-flash` model for the two QA calls (keeping `deepseek-v4-pro` for translation itself) cuts the full-pipeline cost by roughly a third, with no change to translation quality since only the review layer changes model.

Full methodology and page-by-page figures: [`docs/reports/executive-summary-2026-07-23.html`](docs/reports/executive-summary-2026-07-23.html) · reproducible via [`scripts/estimate_page_cost.py`](scripts/estimate_page_cost.py).

---

## Features

| Component | What it does |
|---|---|
| **Translator** (`app/translation/deepseek_client.py`) | Sends source text + relevant glossary subset to DeepSeek in JSON mode, returns a validated `TranslationResult` (translation, confidence, issues, terminology used) |
| **Technical Reviewer** | Independent second call comparing source vs. translation for semantic drift |
| **Terminology Validator** | Independent third call auditing mandatory glossary compliance |
| **Glossary Engine** (`app/translation/glossary.py`) | Loads domain terminology from JSON, sends only the subset relevant to each text (keeps prompts small), plus a free local check for obviously missing mandatory terms |
| **Chunking** (`app/translation/chunking.py`) | Splits long content at paragraph/sentence boundaries — never mid-number or mid-term — and reassembles translated chunks |
| **Content Extraction** (`app/extraction/`) | Walks rendered WordPress/Elementor HTML into semantic blocks (headings, paragraphs, lists, CTAs, alt text, SEO fields), explicitly protecting URLs, emails, and shortcodes from translation |
| **WooCommerce Product Extraction** (`app/extraction/woocommerce_extractor.py`) | Generic — works against any WordPress + WooCommerce site, not just this one. Extracts product name, long/short description, purchase note, attributes/options, gallery image alt text, categories/tags, and SEO. Never extracts SKU, price, stock, weight, or dimensions. Not yet validated against a live WooCommerce site (none in scope) — built and tested against the official `wc/v3/products` schema. |
| **WordPress Connector** (`app/wordpress/`) | Reads posts/pages/meta over the REST API, with dual auth (staging Basic Auth gate + WordPress Application Password) and automatic retry on 429/503 |
| **Translation Memory** (`app/storage/`, `app/synchronization/`) | SQLite-backed content-hash fingerprinting; detects new/changed/unchanged per block so only edited content is ever re-translated |
| **QA Engine** (`app/qa/`) | Numeric consistency, protected-term survival, and URL-preservation checks, combined with the Reviewer's verdict into a 0–100 score and an `auto_approve` / `human_review` / `reject` decision |

---

## Project Status

| Phase | Scope | Status |
|---|---|---|
| 0 | WordPress/WPML environment audit | 🟡 Mostly done — **WPML is not installed on staging**, blocking phases 1, 2.4, 8, 9 |
| 1 | `gnss-bridge` connector plugin | ⚪ Designed, not deployed |
| 2 | WordPress connector | 🟢 Read side done and validated against real staging content |
| 3 | Content extraction (posts, pages, WooCommerce products) | 🟢 Complete — 171 blocks extracted from a real page including excerpt, social SEO fields, featured image, and categories |
| 4 | Translator, Reviewer, Terminology Validator, chunking | 🟢 Complete — 60+ tests, validated against the real DeepSeek API |
| 5 | Glossary Engine | 🟢 Complete (seed glossary, pending expansion with real site terminology) |
| 6 | Translation memory & change detection | 🟢 Complete |
| 7 | QA scoring engine | 🟢 Complete |
| 8 | WPML orchestration, end to end | 🔴 Blocked — needs WPML |
| 9 | Pilot on 5 real pages | 🔴 Blocked — needs WPML |
| 10 | Scale-out & scheduled sync | ⚪ Not started |

**164 automated tests, all passing.** Full phase-by-phase detail: [`ROADMAP.md`](ROADMAP.md), [`PLA-ACCIO.md`](PLA-ACCIO.md), running session history in [`LOG.md`](LOG.md).

---

## Getting Started

```bash
python -m venv .venv
.venv/Scripts/activate   # Windows; use `source .venv/bin/activate` on macOS/Linux
pip install -r requirements.txt
cp .env.example .env     # fill in your own credentials — never commit .env
```

Run the test suite:

```bash
pytest -v
```

Try a real translation (requires a `DEEPSEEK_API_KEY` in `.env`):

```bash
python scripts/translate_sample.py
```

## Project Structure

```
app/
├── translation/     # DeepSeek client, prompts, glossary, chunking
├── extraction/       # HTML → semantic content blocks
├── wordpress/         # REST API client and content reading
├── storage/            # SQLite translation memory
├── synchronization/     # Change detection
└── qa/                    # Automated quality checks and scoring

tests/            # Mirrors app/, 164 tests, no live API/network calls
scripts/          # Manual smoke tests against the real DeepSeek API / staging site
docs/             # Implementation plans, executive summary reports
```

## Documentation

- [`BIBLIOGRAFIA.md`](BIBLIOGRAFIA.md) — research and sources behind every architectural decision
- [`ROADMAP.md`](ROADMAP.md) — phase-by-phase development plan
- [`PLA-ACCIO.md`](PLA-ACCIO.md) — task-level action plan with verification criteria
- [`MEMORIA.md`](MEMORIA.md) — project decisions and context
- [`AUDITORIA-INICIAL.md`](AUDITORIA-INICIAL.md) — findings from the real staging environment audit
- [`LOG.md`](LOG.md) — chronological session log

---

*Private project for Precision-GNSS.com.*
