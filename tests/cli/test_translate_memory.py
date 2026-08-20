"""Integration of the cross-page translation memory into `translate_block`."""
from unittest.mock import MagicMock

from app.cli.translate import translate_block
from app.extraction.schemas import ContentBlock
from app.storage.translation_memory import TranslationMemory
from app.translation.schemas import ReviewResult, TranslationResult

FP = "fingerprint1"


def _deepseek(translation: str, passed: bool = True) -> MagicMock:
    client = MagicMock()
    client.translate.return_value = TranslationResult(translation=translation, confidence=0.97)
    client.review.return_value = ReviewResult(passed=passed)
    return client


def _block(source: str = "Request a quote", content_id: str = "b1") -> ContentBlock:
    return ContentBlock(content_id=content_id, type="paragraph", context="", source=source, translate=True)


def _memory(tmp_path) -> TranslationMemory:
    return TranslationMemory(tmp_path / "tm.sqlite3")


def test_an_approved_translation_is_remembered(tmp_path):
    memory = _memory(tmp_path)
    translate_block(_deepseek("Solicitar presupuesto"), _block(), "es", "European Spanish", [],
                    memory=memory, fingerprint=FP)

    assert memory.lookup("Request a quote", "es", FP) == "Solicitar presupuesto"


def test_a_flagged_translation_is_not_remembered(tmp_path):
    # Only auto_approve is trusted enough to be served again elsewhere.
    memory = _memory(tmp_path)
    translate_block(_deepseek("Solicitar presupuesto", passed=False), _block(), "es", "European Spanish", [],
                    memory=memory, fingerprint=FP)

    assert memory.lookup("Request a quote", "es", FP) is None


def test_a_hit_skips_both_ai_calls(tmp_path):
    memory = _memory(tmp_path)
    memory.remember("Request a quote", "Solicitar presupuesto", "es", FP)
    deepseek = _deepseek("should never be called")

    result = translate_block(deepseek, _block(), "es", "European Spanish", [], memory=memory, fingerprint=FP)

    assert result.translation == "Solicitar presupuesto"
    assert result.from_memory is True
    deepseek.translate.assert_not_called()
    deepseek.review.assert_not_called()


def test_a_hit_still_scores_as_auto_approve(tmp_path):
    memory = _memory(tmp_path)
    memory.remember("Request a quote", "Solicitar presupuesto", "es", FP)

    result = translate_block(_deepseek("x"), _block(), "es", "European Spanish", [], memory=memory, fingerprint=FP)

    assert result.qa.decision == "auto_approve"
    assert result.qa.score == 100


def test_a_fresh_translation_is_not_marked_as_reused(tmp_path):
    result = translate_block(_deepseek("Solicitar presupuesto"), _block(), "es", "European Spanish", [],
                             memory=_memory(tmp_path), fingerprint=FP)

    assert result.from_memory is False


def test_a_stale_entry_failing_a_mechanical_check_is_not_reused(tmp_path):
    # The decided protocol: re-run the four mechanical checks on every hit and
    # refuse the entry if any fails, rather than trusting it blindly.
    memory = _memory(tmp_path)
    memory.remember("Accuracy of 1 cm", "Precisión de 2 cm", "es", FP)
    deepseek = _deepseek("Precisión de 1 cm")

    result = translate_block(deepseek, _block("Accuracy of 1 cm"), "es", "European Spanish", [],
                             memory=memory, fingerprint=FP)

    assert result.from_memory is False
    assert result.translation == "Precisión de 1 cm"
    deepseek.translate.assert_called_once()


def test_a_refused_entry_is_overwritten_by_the_fresh_translation(tmp_path):
    memory = _memory(tmp_path)
    memory.remember("Accuracy of 1 cm", "Precisión de 2 cm", "es", FP)

    translate_block(_deepseek("Precisión de 1 cm"), _block("Accuracy of 1 cm"), "es", "European Spanish", [],
                    memory=memory, fingerprint=FP)

    assert memory.lookup("Accuracy of 1 cm", "es", FP) == "Precisión de 1 cm"


def test_a_different_fingerprint_does_not_reuse(tmp_path):
    memory = _memory(tmp_path)
    memory.remember("Request a quote", "Solicitar presupuesto", "es", "old-fingerprint")
    deepseek = _deepseek("Pedir presupuesto")

    result = translate_block(deepseek, _block(), "es", "European Spanish", [], memory=memory, fingerprint=FP)

    assert result.from_memory is False
    deepseek.translate.assert_called_once()


def test_without_a_memory_nothing_changes(tmp_path):
    deepseek = _deepseek("Solicitar presupuesto")

    result = translate_block(deepseek, _block(), "es", "European Spanish", [])

    assert result.translation == "Solicitar presupuesto"
    assert result.from_memory is False
    deepseek.translate.assert_called_once()


def test_a_non_translatable_block_never_touches_the_memory(tmp_path):
    memory = _memory(tmp_path)
    block = ContentBlock(content_id="b1", type="alt_text", context="",
                         source="https://example.com", translate=False)

    translate_block(_deepseek("x"), block, "es", "European Spanish", [], memory=memory, fingerprint=FP)

    assert memory.stats()["entries"] == 0


def test_reuse_repairs_lost_spacing_the_same_way_a_fresh_run_would(tmp_path):
    # A stored entry predating the structure checker could still be glued.
    memory = _memory(tmp_path)
    source = 'Use 2x <a href="https://example.com/k">Starter Kits</a> today.'
    memory.remember(source, 'Usa 2x<a href="https://example.com/k">Kits Iniciales</a> hoy.', "es", FP)

    result = translate_block(_deepseek("x"), _block(source), "es", "European Spanish", [],
                             memory=memory, fingerprint=FP)

    assert result.from_memory is True
    assert "2x <a" in result.translation
