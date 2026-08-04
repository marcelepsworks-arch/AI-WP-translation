"""WPMLAdapter: writes translations to WordPress via the gnss-bridge
mu-plugin's REST endpoints (ROADMAP.md FASE 1/8, BIBLIOGRAFIA.md §2/§11).

Two write paths, matching the two endpoint groups documented on gnss-bridge:
- `get_wpml_status()` / `link_translation()`: the original hooks-based path,
  wrapping `wpml_set_element_language_details` directly.
- `create_job()` / `export_xliff()` / `import_xliff()` (and the `start_job()`
  / `complete_job()` helpers that sequence them): the "local translator" +
  Translation Management job path (BIBLIOGRAFIA.md §11).

gnss-bridge itself is not deployed yet — WPML is not installed on staging
(MEMORIA.md 2026-08-04). This module is built against the endpoint contract
already documented in ROADMAP.md/PLA-ACCIO.md and is tested with mocked HTTP
responses; the exact request/response shapes have not been validated against
a real gnss-bridge deployment yet (PLA-ACCIO.md task 1.8).
"""
from __future__ import annotations

from app.extraction.schemas import ContentBlock
from app.wordpress.client import WordPressClient
from app.wordpress.xliff import build_translated_xliff, parse_xliff

_BRIDGE_PREFIX = "/wp-json/gnss-bridge/v1"


def get_wpml_status(client: WordPressClient, post_id: int) -> dict:
    return client.get(f"{_BRIDGE_PREFIX}/translation-status/{post_id}").json()


def link_translation(
    client: WordPressClient,
    element_id: int,
    trid: int,
    language_code: str,
    source_language_code: str,
) -> dict:
    return client.post(
        f"{_BRIDGE_PREFIX}/link-translation",
        json={
            "element_id": element_id,
            "trid": trid,
            "language_code": language_code,
            "source_language_code": source_language_code,
        },
    ).json()


def create_job(client: WordPressClient, element_id: int, language_code: str) -> dict:
    return client.post(
        f"{_BRIDGE_PREFIX}/create-job",
        json={"element_id": element_id, "language_code": language_code},
    ).json()


def export_xliff(client: WordPressClient, job_id: int) -> str:
    return client.get(f"{_BRIDGE_PREFIX}/export-xliff/{job_id}").text


def import_xliff(client: WordPressClient, xliff_content: str) -> dict:
    return client.post(f"{_BRIDGE_PREFIX}/import-xliff", json={"xliff": xliff_content}).json()


def start_job(
    client: WordPressClient, element_id: int, language_code: str
) -> tuple[str, list[ContentBlock]]:
    """Create a Translation Management job and export it as XLIFF.

    Returns the raw XLIFF (needed later by `complete_job`) and the
    ContentBlocks parsed from it, ready to feed into the translation
    pipeline (FASE 4-7).
    """
    job = create_job(client, element_id, language_code)
    xliff_content = export_xliff(client, job["job_id"])
    return xliff_content, parse_xliff(xliff_content)


def complete_job(client: WordPressClient, xliff_content: str, translations: dict[str, str]) -> dict:
    """Insert translated segments into the exported XLIFF and import it
    back into WPML, completing the job started by `start_job`.
    """
    translated_xliff = build_translated_xliff(xliff_content, translations)
    return import_xliff(client, translated_xliff)
