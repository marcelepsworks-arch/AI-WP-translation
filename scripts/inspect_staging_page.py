"""Manual smoke test: fetch one real page from the staging site and
print what the connector actually sees.

Usage:
    python scripts/inspect_staging_page.py <page_id>

Reads credentials from .env — never hardcode them here.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

from app.wordpress.client import WordPressClient
from app.wordpress.content import get_elementor_data, get_page, get_page_meta


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
    meta = get_page_meta(client, page_id)
    elementor_data = get_elementor_data(meta)

    print(f"Title:          {page['title']['rendered']}")
    print(f"Slug:           {page['slug']}")
    print(f"Content length: {len(page['content']['rendered'])} chars (rendered HTML)")
    print(f"Meta keys:      {list(meta.keys())}")
    print(f"Elementor data exposed via REST: {'yes' if elementor_data else 'no'}")


if __name__ == "__main__":
    main()
