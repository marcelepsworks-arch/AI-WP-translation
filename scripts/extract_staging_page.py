"""Manual smoke test: extract semantic content blocks from one real
staging page and print them.

Usage:
    python scripts/extract_staging_page.py <page_id>

Reads credentials from .env — never hardcode them here.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

if sys.stdout.encoding is not None and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

from app.extraction.content_extractor import extract_page_content
from app.wordpress.client import WordPressClient
from app.wordpress.content import get_page


def main() -> None:
    load_dotenv()

    page_id = int(sys.argv[1]) if len(sys.argv) > 1 else 4309  # Precision Agriculture

    client = WordPressClient(
        base_url=os.environ["STAGING_URL"],
        basic_auth=(os.environ["STAGING_BASIC_AUTH_USER"], os.environ["STAGING_BASIC_AUTH_PASSWORD"]),
        wp_username=os.environ.get("WP_USERNAME"),
        wp_app_password=os.environ.get("WP_APPLICATION_PASSWORD"),
    )

    page = get_page(client, page_id)
    blocks = extract_page_content(page)

    translatable = [b for b in blocks if b.translate]
    protected = [b for b in blocks if not b.translate]

    print(f"Page: {page['title']['rendered']} (id={page_id})")
    print(f"Total blocks: {len(blocks)}  |  translatable: {len(translatable)}  |  protected/skipped: {len(protected)}")
    print()
    for block in blocks[:20]:
        flag = "T" if block.translate else "-"
        context = f" [{block.context}]" if block.context else ""
        print(f"[{flag}] {block.type:<15}{context}  {block.source[:80]}")
    if len(blocks) > 20:
        print(f"... and {len(blocks) - 20} more blocks")


if __name__ == "__main__":
    main()
