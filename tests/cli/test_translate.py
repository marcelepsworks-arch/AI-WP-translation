from unittest.mock import MagicMock

from app.cli.translate import (
    BlockResult,
    overall_decision,
    reassemble_body_html,
    resolve_publish_status,
    translate_block,
    translate_blocks,
    translate_page,
)
from app.extraction.schemas import ContentBlock
from app.translation.glossary import GlossaryEntry
from app.translation.schemas import ReviewResult, TranslationResult


def _deepseek(translation: str, confidence: float = 0.97, passed: bool = True) -> MagicMock:
    client = MagicMock()
    client.translate.return_value = TranslationResult(translation=translation, confidence=confidence)
    client.review.return_value = ReviewResult(passed=passed)
    return client


def test_translate_block_skips_non_translatable_blocks():
    block = ContentBlock(content_id="b1", type="alt_text", context="", source="https://example.com", translate=False)
    deepseek = _deepseek("should not be called")

    result = translate_block(deepseek, block, "es", "European Spanish", [])

    assert result.translation == block.source
    assert result.qa is None
    deepseek.translate.assert_not_called()


def test_translate_block_calls_translate_and_review_and_scores_result():
    block = ContentBlock(content_id="b1", type="paragraph", context="Ctx", source="The rover is fast.", translate=True)
    deepseek = _deepseek("El rover es rápido.")

    result = translate_block(deepseek, block, "es", "European Spanish", [])

    deepseek.translate.assert_called_once_with(
        "The rover is fast.", "European Spanish", context="Ctx", glossary_terms=[]
    )
    deepseek.review.assert_called_once_with("The rover is fast.", "El rover es rápido.", "European Spanish")
    assert result.translation == "El rover es rápido."
    assert result.qa is not None
    assert result.qa.decision == "auto_approve"


def test_translate_block_sanitizes_html_in_deepseek_response_before_qa_and_result():
    block = ContentBlock(content_id="b1", type="paragraph", context="", source="Click here.", translate=True)
    deepseek = _deepseek('Haz clic <script>alert(1)</script>aqui <a href="javascript:alert(2)">enlace</a>.')

    result = translate_block(deepseek, block, "es", "European Spanish", [])

    assert "<script" not in result.translation
    assert "javascript:" not in result.translation
    # The Reviewer must see the already-sanitized text, not the raw response.
    deepseek.review.assert_called_once_with(
        "Click here.", "Haz clic aqui <a>enlace</a>.", "European Spanish"
    )


def test_translate_block_passes_relevant_glossary_terms():
    entries = [GlossaryEntry(source="rover", target="rover", language="es", status="mandatory")]
    block = ContentBlock(content_id="b1", type="paragraph", context="", source="The rover moves.", translate=True)
    deepseek = _deepseek("El rover se mueve.")

    translate_block(deepseek, block, "es", "European Spanish", entries)

    _, kwargs = deepseek.translate.call_args
    assert kwargs["glossary_terms"][0].source == "rover"


def test_translate_block_flags_reject_on_numeric_mismatch():
    block = ContentBlock(content_id="b1", type="paragraph", context="", source="1 cm accuracy", translate=True)
    deepseek = _deepseek("2 cm de precisión")

    result = translate_block(deepseek, block, "es", "European Spanish", [])

    assert result.qa.decision == "reject"


def test_translate_block_logs_review_issues_when_review_fails(caplog):
    import logging

    caplog.set_level(logging.WARNING, logger="app.cli.translate")

    block = ContentBlock(content_id="b1", type="paragraph", context="", source="text", translate=True)
    deepseek = _deepseek("texto", passed=False)
    deepseek.review.return_value = ReviewResult(
        passed=False, issues=[{"type": "meaning_change", "description": "tone shifted"}]
    )

    translate_block(deepseek, block, "es", "European Spanish", [])

    warning = next(r for r in caplog.records if r.levelname == "WARNING")
    assert "tone shifted" in warning.message
    assert "text" in warning.message
    assert "texto" in warning.message


def test_translate_blocks_maps_over_all_blocks():
    blocks = [
        ContentBlock(content_id="b1", type="title", context="", source="Hello", translate=True),
        ContentBlock(content_id="b2", type="alt_text", context="", source="", translate=False),
    ]
    deepseek = _deepseek("Hola")

    results = translate_blocks(deepseek, blocks, "es", [])

    assert [r.content_id for r in results] == ["b1", "b2"]
    assert results[0].translation == "Hola"
    assert results[1].translation == ""


def test_translate_blocks_prints_live_progress(capsys):
    blocks = [ContentBlock(content_id="b1", type="paragraph", context="", source="Hi", translate=True)]
    deepseek = _deepseek("Hola")

    translate_blocks(deepseek, blocks, "es", [])

    out = capsys.readouterr().out
    assert "[1/1] translating b1" in out
    assert "[1/1] b1 -> auto_approve" in out


def test_translate_blocks_with_max_workers_preserves_order_and_correctness():
    blocks = [
        ContentBlock(content_id=f"b{i}", type="paragraph", context="", source=f"Text {i}", translate=True)
        for i in range(5)
    ]

    def translate_side_effect(source_text, target_language_name, context="", glossary_terms=None):
        return TranslationResult(translation=source_text.replace("Text", "Texto"), confidence=0.9)

    deepseek = MagicMock()
    deepseek.translate.side_effect = translate_side_effect
    deepseek.review.return_value = ReviewResult(passed=True)

    results = translate_blocks(deepseek, blocks, "es", [], max_workers=3)

    assert [r.content_id for r in results] == ["b0", "b1", "b2", "b3", "b4"]
    assert [r.translation for r in results] == [f"Texto {i}" for i in range(5)]


def test_overall_decision_is_auto_approve_when_nothing_needed_translation():
    results = [BlockResult(content_id="b1", type="alt_text", source="x", translation="x", qa=None)]

    assert overall_decision(results) == "auto_approve"


def test_overall_decision_is_reject_when_any_block_rejected():
    from app.qa.scoring import QAReport

    results = [
        BlockResult(
            content_id="b1", type="paragraph", source="a", translation="a",
            qa=QAReport(numeric_passed=True, terminology_passed=True, url_passed=True, structure_passed=True, review_passed=True, score=100, decision="auto_approve"),
        ),
        BlockResult(
            content_id="b2", type="paragraph", source="b", translation="b",
            qa=QAReport(numeric_passed=False, terminology_passed=True, url_passed=True, structure_passed=True, review_passed=True, score=60, decision="reject"),
        ),
    ]

    assert overall_decision(results) == "reject"


def test_overall_decision_is_human_review_when_no_reject_but_some_human_review():
    from app.qa.scoring import QAReport

    results = [
        BlockResult(
            content_id="b1", type="paragraph", source="a", translation="a",
            qa=QAReport(numeric_passed=True, terminology_passed=True, url_passed=True, structure_passed=True, review_passed=False, score=70, decision="human_review"),
        ),
    ]

    assert overall_decision(results) == "human_review"


def test_resolve_publish_status_off_always_drafts():
    assert resolve_publish_status("off", "auto_approve") == "draft"
    assert resolve_publish_status("off", "reject") == "draft"


def test_resolve_publish_status_qa_gated_publishes_only_auto_approve():
    assert resolve_publish_status("qa_gated", "auto_approve") == "publish"
    assert resolve_publish_status("qa_gated", "human_review") == "draft"
    assert resolve_publish_status("qa_gated", "reject") == "draft"


def test_resolve_publish_status_all_always_publishes():
    assert resolve_publish_status("all", "auto_approve") == "publish"
    assert resolve_publish_status("all", "reject") == "publish"


def test_reassemble_body_html_wraps_headings_and_paragraphs_with_translations():
    blocks = [
        ContentBlock(content_id="b1", type="heading", context="", source="Title", translate=True),
        ContentBlock(content_id="b2", type="paragraph", context="", source="Body text", translate=True),
    ]
    results_by_id = {
        "b1": BlockResult(content_id="b1", type="heading", source="Title", translation="Título"),
        "b2": BlockResult(content_id="b2", type="paragraph", source="Body text", translation="Texto"),
    }

    html = reassemble_body_html(blocks, results_by_id)

    assert html == "<h2>Título</h2>\n<p>Texto</p>"


def test_reassemble_body_html_skips_non_body_block_types():
    blocks = [
        ContentBlock(content_id="b1", type="seo_title", context="", source="SEO", translate=True),
        ContentBlock(content_id="b2", type="paragraph", context="", source="Body", translate=True),
    ]
    results_by_id = {
        "b1": BlockResult(content_id="b1", type="seo_title", source="SEO", translation="SEO ES"),
        "b2": BlockResult(content_id="b2", type="paragraph", source="Body", translation="Cuerpo"),
    }

    html = reassemble_body_html(blocks, results_by_id)

    assert "SEO" not in html
    assert html == "<p>Cuerpo</p>"


def _page_payload(post_id: int = 42) -> dict:
    return {
        "id": post_id,
        "title": {"rendered": "Hello"},
        "excerpt": {"rendered": ""},
        "content": {"rendered": "<p>The rover moves.</p>"},
        "yoast_head_json": None,
    }


def test_translate_page_dry_run_does_not_write_anything():
    wp_client = MagicMock()
    wp_client.get.return_value.json.return_value = _page_payload()
    deepseek = _deepseek("El rover se mueve.")

    result = translate_page(wp_client, deepseek, [], post_id=42, dry_run=True)

    assert result.written is False
    wp_client.post.assert_not_called()


def test_translate_page_still_writes_as_draft_when_overall_decision_is_reject():
    # Policy changed 2026-08-06 (MEMORIA.md): on a long page some block gets
    # flagged near-certainly, so a single reject no longer blocks the whole
    # draft -- it's always written as a draft (never published either way)
    # and flagged blocks are logged for human review instead.
    wp_client = MagicMock()
    wp_client.get.return_value.json.return_value = {
        "id": 42, "title": {"rendered": "1 cm accuracy"}, "excerpt": {"rendered": ""},
        "content": {"rendered": ""}, "yoast_head_json": None,
    }
    wp_client.post.return_value.json.return_value = {"id": 99}
    deepseek = _deepseek("2 cm de precisión")  # numeric mismatch -> reject

    result = translate_page(wp_client, deepseek, [], post_id=42, dry_run=False)

    assert result.written is True
    assert result.overall_decision == "reject"
    assert result.translated_post_id == 99
    create_call = wp_client.post.call_args_list[0]
    assert create_call.kwargs["json"]["status"] == "draft"


def test_translate_page_translates_elementor_data_and_writes_it_to_meta():
    import json

    elementor_data = json.dumps([
        {"id": "h1", "elType": "widget", "widgetType": "heading", "settings": {"title": "The rover moves."}},
    ])
    page_with_elementor = {
        **_page_payload(),
        # Deliberately non-empty and matching the Elementor content, to prove
        # skip_body kicks in -- if it didn't, this would get extracted AND
        # translated a second time alongside the Elementor block.
        "content": {"rendered": "<p>The rover moves.</p>"},
        "meta": {"_elementor_data": elementor_data, "_elementor_edit_mode": "builder"},
    }

    wp_client = MagicMock()

    def fake_get(path, params=None):
        resp = MagicMock()
        if "translation-status" in path:
            resp.json.return_value = {"element_id": 42, "trid": 13329, "language_code": "en"}
        else:
            resp.json.return_value = page_with_elementor
        return resp

    wp_client.get.side_effect = fake_get
    wp_client.post.return_value.json.return_value = {"id": 99}
    deepseek = _deepseek("El rover se mueve.")

    result = translate_page(wp_client, deepseek, [], post_id=42, dry_run=False)

    # title (not part of the body) + the one Elementor heading field.
    # skip_body must have suppressed the redundant content.rendered
    # extraction -- otherwise a second "heading"-type block for the same
    # text would also appear here, translated a second time.
    assert [b.type for b in result.blocks] == ["title", "elementor_heading_title"]
    assert deepseek.translate.call_count == 2

    create_call = wp_client.post.call_args_list[0]
    written_meta = create_call.kwargs["json"]["meta"]
    rebuilt = json.loads(written_meta["_elementor_data"])

    assert rebuilt[0]["settings"]["title"] == "El rover se mueve."
    assert rebuilt[0]["id"] == "h1"
    assert written_meta["_elementor_edit_mode"] == "builder"


def test_translate_page_writes_draft_and_links_translation_when_approved():
    wp_client = MagicMock()

    def fake_get(path, params=None):
        resp = MagicMock()
        if "translation-status" in path:
            resp.json.return_value = {"element_id": 42, "trid": 13329, "language_code": "en"}
        else:
            resp.json.return_value = _page_payload()
        return resp

    wp_client.get.side_effect = fake_get
    wp_client.post.return_value.json.return_value = {"id": 99}
    deepseek = _deepseek("El rover se mueve.")

    result = translate_page(wp_client, deepseek, [], post_id=42, post_type="page", target_language="es", dry_run=False)

    assert result.written is True
    assert result.translated_post_id == 99

    create_call = wp_client.post.call_args_list[0]
    assert create_call.args[0] == "/wp-json/wp/v2/pages"
    assert create_call.kwargs["json"]["status"] == "draft"

    link_call = wp_client.post.call_args_list[1]
    assert link_call.args[0] == "/wp-json/gnss-bridge/v1/link-translation"
    assert link_call.kwargs["json"] == {
        "element_id": 99,
        "trid": 13329,
        "language_code": "es",
        "source_language_code": "en",
    }


def test_translate_page_publishes_live_under_qa_gated_when_auto_approved():
    wp_client = MagicMock()

    def fake_get(path, params=None):
        resp = MagicMock()
        if "translation-status" in path:
            resp.json.return_value = {"element_id": 42, "trid": 13329, "language_code": "en"}
        else:
            resp.json.return_value = _page_payload()
        return resp

    wp_client.get.side_effect = fake_get
    wp_client.post.return_value.json.return_value = {"id": 99}
    deepseek = _deepseek("El rover se mueve.")  # auto_approve

    translate_page(
        wp_client, deepseek, [], post_id=42, post_type="page", target_language="es",
        dry_run=False, auto_publish_mode="qa_gated",
    )

    create_call = wp_client.post.call_args_list[0]
    assert create_call.kwargs["json"]["status"] == "publish"


def test_translate_page_still_drafts_under_qa_gated_when_flagged():
    wp_client = MagicMock()
    wp_client.get.return_value.json.return_value = {
        "id": 42, "title": {"rendered": "1 cm accuracy"}, "excerpt": {"rendered": ""},
        "content": {"rendered": ""}, "yoast_head_json": None,
    }
    wp_client.post.return_value.json.return_value = {"id": 99}
    deepseek = _deepseek("2 cm de precisión")  # numeric mismatch -> reject

    translate_page(
        wp_client, deepseek, [], post_id=42, dry_run=False, auto_publish_mode="qa_gated",
    )

    create_call = wp_client.post.call_args_list[0]
    assert create_call.kwargs["json"]["status"] == "draft"


def test_translate_page_writes_progress_html_when_path_given(tmp_path):
    from pathlib import Path

    wp_client = MagicMock()
    wp_client.get.return_value.json.return_value = _page_payload()
    deepseek = _deepseek("El rover se mueve.")
    html_path = Path(tmp_path) / "progress.html"

    result = translate_page(wp_client, deepseek, [], post_id=42, dry_run=True, progress_html_path=html_path)

    assert result.overall_decision == "auto_approve"
    assert html_path.exists()
    content = html_path.read_text(encoding="utf-8")
    assert "Finished" in content
    assert "auto_approve" in content


def test_translate_page_warns_and_skips_linking_when_no_trid_found():
    wp_client = MagicMock()

    def fake_get(path, params=None):
        resp = MagicMock()
        if "translation-status" in path:
            resp.json.return_value = {"element_id": 42, "trid": None, "language_code": None}
        else:
            resp.json.return_value = _page_payload()
        return resp

    wp_client.get.side_effect = fake_get
    wp_client.post.return_value.json.return_value = {"id": 99}
    deepseek = _deepseek("El rover se mueve.")

    result = translate_page(wp_client, deepseek, [], post_id=42, dry_run=False)

    assert result.written is True
    assert result.translated_post_id == 99
    # Only the draft-creation POST happened -- no link-translation call.
    assert wp_client.post.call_count == 1


def test_translate_page_logs_key_events(caplog):
    import logging

    caplog.set_level(logging.INFO, logger="app.cli.translate")

    wp_client = MagicMock()

    def fake_get(path, params=None):
        resp = MagicMock()
        if "translation-status" in path:
            resp.json.return_value = {"element_id": 42, "trid": 13329, "language_code": "en"}
        else:
            resp.json.return_value = _page_payload()
        return resp

    wp_client.get.side_effect = fake_get
    wp_client.post.return_value.json.return_value = {"id": 99}
    deepseek = _deepseek("El rover se mueve.")

    translate_page(wp_client, deepseek, [], post_id=42, target_language="es", dry_run=False)

    messages = "\n".join(caplog.messages)
    assert "fetching page 42" in messages
    assert "overall decision for page 42" in messages
    assert "created draft page 99" in messages
    assert "linked page 99 to trid 13329" in messages


def test_translate_page_logs_warning_listing_flagged_blocks_when_not_auto_approved(caplog):
    import logging

    caplog.set_level(logging.INFO, logger="app.cli.translate")

    wp_client = MagicMock()
    wp_client.get.return_value.json.return_value = {
        "id": 42, "title": {"rendered": "1 cm accuracy"}, "excerpt": {"rendered": ""},
        "content": {"rendered": ""}, "yoast_head_json": None,
    }
    wp_client.post.return_value.json.return_value = {"id": 99}
    deepseek = _deepseek("2 cm de precisión")

    translate_page(wp_client, deepseek, [], post_id=42, dry_run=False)

    warning = next(r for r in caplog.records if r.levelname == "WARNING" and "human review" in r.message)
    assert "page_42_title" in warning.message
