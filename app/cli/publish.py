"""Writes a previously reviewed translation (produced by
`app.cli.translate --review`) to WordPress, without re-calling DeepSeek.

Usage:
    python -m app.cli.publish --review logs/review_6273_es.json

The review JSON already contains the exact WP payload built at translation
time (title/content/meta/status) -- this script only does the WordPress
write + WPML linking step that `translate_page` would otherwise have done
immediately.
"""
from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

from app.cli.translate import PageReview, configure_logging, write_and_link_translation
from app.wordpress.client import WordPressClient

logger = logging.getLogger(__name__)


def _build_wp_client() -> WordPressClient:
    base_url = os.environ.get("WP_URL") or os.environ["STAGING_URL"]
    basic_auth = None
    if os.environ.get("STAGING_BASIC_AUTH_USER"):
        basic_auth = (os.environ["STAGING_BASIC_AUTH_USER"], os.environ["STAGING_BASIC_AUTH_PASSWORD"])
    return WordPressClient(
        base_url=base_url,
        basic_auth=basic_auth,
        wp_username=os.environ.get("WP_USERNAME"),
        wp_app_password=os.environ.get("WP_APPLICATION_PASSWORD"),
    )


def publish_review(wp_client: WordPressClient, review: PageReview) -> int:
    endpoint = f"/wp-json/wp/v2/{'pages' if review.post_type == 'page' else 'posts'}"
    return write_and_link_translation(
        wp_client, endpoint, review.payload, review.post_id, review.post_type, review.target_language
    )


def main() -> None:
    from dotenv import load_dotenv

    load_dotenv()
    configure_logging()

    parser = argparse.ArgumentParser(description="Publish a reviewed translation artifact to WordPress.")
    parser.add_argument("--review", type=Path, required=True, help="Path to the review_*.json file to publish")
    args = parser.parse_args()

    review = PageReview.model_validate_json(args.review.read_text(encoding="utf-8"))
    wp_client = _build_wp_client()

    translated_post_id = publish_review(wp_client, review)
    print(f"Published: {review.post_type} {translated_post_id} ({review.target_language} translation of {review.post_id})")


if __name__ == "__main__":
    main()
