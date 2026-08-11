import json
from unittest.mock import MagicMock

from app.cli.sync import sync_page
from app.cli.translate import hash_source
from app.translation.schemas import ReviewResult, TranslationResult


def _deepseek(translation: str = "El rover se mueve.") -> MagicMock:
    client = MagicMock()
    client.translate.return_value = TranslationResult(translation=translation, confidence=0.97)
    client.review.return_value = ReviewResult(passed=True)
    client.usage = {}
    return client


def _page_payload(post_id: int = 42, title: str = "The rover moves.") -> dict:
    return {
        "id": post_id,
        "title": {"rendered": title},
        "excerpt": {"rendered": ""},
        "content": {"rendered": ""},
        "yoast_head_json": None,
    }


def test_sync_page_creates_when_no_translation_exists():
    wp_client = MagicMock()

    def fake_get(path, params=None):
        resp = MagicMock()
        if "translation-status" in path:
            resp.json.return_value = {
                "element_id": 42, "trid": 13329, "language_code": "en",
                "translation_exists": False, "translated_post_id": None, "needs_update": None,
            }
        else:
            resp.json.return_value = _page_payload()
        return resp

    wp_client.get.side_effect = fake_get
    wp_client.post.return_value.json.return_value = {"id": 99}
    deepseek = _deepseek()

    result = sync_page(wp_client, deepseek, [], post_id=42, post_type="page", target_language="es")

    assert result.outcome == "created"
    assert result.translated_post_id == 99
    create_call = wp_client.post.call_args_list[0]
    assert create_call.args[0] == "/wp-json/wp/v2/pages"


def test_sync_page_does_nothing_when_up_to_date():
    wp_client = MagicMock()
    wp_client.get.return_value.json.return_value = {
        "element_id": 42, "trid": 13329, "language_code": "en",
        "translation_exists": True, "translated_post_id": 99, "needs_update": False,
    }
    deepseek = _deepseek()

    result = sync_page(wp_client, deepseek, [], post_id=42, post_type="page", target_language="es")

    assert result.outcome == "up_to_date"
    assert result.translated_post_id == 99
    deepseek.translate.assert_not_called()
    wp_client.post.assert_not_called()


def test_sync_page_updates_only_changed_blocks():
    wp_client = MagicMock()

    unchanged_hash = hash_source("Unchanged paragraph.")

    def fake_get(path, params=None):
        resp = MagicMock()
        if "translation-status" in path:
            resp.json.return_value = {
                "element_id": 42, "trid": 13329, "language_code": "en",
                "translation_exists": True, "translated_post_id": 99, "needs_update": True,
            }
        elif path == "/wp-json/wp/v2/pages/42":
            resp.json.return_value = _page_payload(post_id=42, title="The rover moves fast now.")
        elif path == "/wp-json/wp/v2/pages/99":
            resp.json.return_value = {
                "id": 99,
                "meta": {
                    "_gnss_block_hashes": json.dumps(
                        {
                            "page_42_title": {"hash": hash_source("The rover moves."), "translation": "El rover se mueve."},
                        }
                    )
                },
            }
        else:
            raise AssertionError(f"unexpected GET {path}")
        return resp

    wp_client.get.side_effect = fake_get
    deepseek = _deepseek(translation="El rover se mueve rápido ahora.")

    result = sync_page(wp_client, deepseek, [], post_id=42, post_type="page", target_language="es")

    assert result.outcome == "updated"
    assert result.blocks_translated == 1
    deepseek.translate.assert_called_once()

    update_call = wp_client.post.call_args_list[0]
    assert update_call.args[0] == "/wp-json/wp/v2/pages/99"
    assert update_call.kwargs["json"]["title"] == "El rover se mueve rápido ahora."
