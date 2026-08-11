"""Read-only WordPress content access: posts, pages, meta, Elementor data.

WPML-related functions (get_wpml_status, link_translation) are
intentionally not here yet — WPML is not installed on staging as of
2026-07-23 (see AUDITORIA-INICIAL.md section 0.2).
"""
from __future__ import annotations

from app.wordpress.client import WordPressClient


def get_post(client: WordPressClient, post_id: int) -> dict:
    return client.get(f"/wp-json/wp/v2/posts/{post_id}").json()


def get_page(client: WordPressClient, page_id: int) -> dict:
    return client.get(f"/wp-json/wp/v2/pages/{page_id}").json()


def get_pages(client: WordPressClient, per_page: int = 100) -> list[dict]:
    return client.get("/wp-json/wp/v2/pages", params={"per_page": per_page}).json()


def get_posts(client: WordPressClient, per_page: int = 100) -> list[dict]:
    return client.get("/wp-json/wp/v2/posts", params={"per_page": per_page}).json()


def get_post_meta(client: WordPressClient, post_id: int) -> dict:
    return get_post(client, post_id).get("meta", {})


def get_page_meta(client: WordPressClient, page_id: int) -> dict:
    return get_page(client, page_id).get("meta", {})


def get_elementor_data(meta: dict) -> str | None:
    return meta.get("_elementor_data")
