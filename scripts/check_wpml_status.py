"""Manual smoke test: check whether WPML is now active on staging by
inspecting the REST API namespace index (same method used for the FASE 0
audit finding in AUDITORIA-INICIAL.md section 0.2).

Usage:
    python scripts/check_wpml_status.py

Reads credentials from .env — never hardcode them here.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

from app.wordpress.client import WordPressClient


def main() -> None:
    load_dotenv()

    client = WordPressClient(
        base_url=os.environ["STAGING_URL"],
        basic_auth=(os.environ["STAGING_BASIC_AUTH_USER"], os.environ["STAGING_BASIC_AUTH_PASSWORD"]),
        wp_username=os.environ.get("WP_USERNAME"),
        wp_app_password=os.environ.get("WP_APPLICATION_PASSWORD"),
    )

    index = client.get("/wp-json/").json()
    namespaces = index.get("namespaces", [])
    wpml_namespaces = [ns for ns in namespaces if ns.startswith("wpml/")]
    gnss_bridge_namespaces = [ns for ns in namespaces if ns.startswith("gnss-bridge/")]

    print(f"All namespaces: {namespaces}")
    print(f"WPML namespaces found: {wpml_namespaces or 'none'}")
    print(f"gnss-bridge namespaces found: {gnss_bridge_namespaces or 'none'}")

    pages_es = client.get("/wp-json/wp/v2/pages", params={"lang": "es", "per_page": 5}).json()
    print(f"wp/v2/pages?lang=es -> {len(pages_es)} results (WPML lang filter accepted without erroring if >0 or empty list, not a 400)")


if __name__ == "__main__":
    main()
