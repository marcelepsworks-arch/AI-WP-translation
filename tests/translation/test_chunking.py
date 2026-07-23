from unittest.mock import MagicMock

from app.translation.chunking import chunk_text, translate_long_text
from app.translation.deepseek_client import DeepSeekClient
from app.translation.prompt_builder import GlossaryTerm
from app.translation.schemas import TranslationResult


def test_chunk_text_returns_single_chunk_when_text_is_short():
    text = "Paragraph one."

    chunks = chunk_text(text, max_chars=100)

    assert chunks == ["Paragraph one."]


def test_chunk_text_keeps_paragraphs_together_when_they_fit():
    text = "Para one.\n\nPara two."

    chunks = chunk_text(text, max_chars=100)

    assert chunks == ["Para one.\n\nPara two."]


def test_chunk_text_splits_paragraphs_that_dont_fit_together():
    para1 = "A" * 50
    para2 = "B" * 50
    text = f"{para1}\n\n{para2}"

    chunks = chunk_text(text, max_chars=60)

    assert chunks == [para1, para2]


def test_chunk_text_never_splits_a_paragraph_that_fits_alone_even_if_combined_exceeds_limit():
    para1 = "A" * 30
    para2 = "B" * 30
    text = f"{para1}\n\n{para2}"

    chunks = chunk_text(text, max_chars=35)

    assert chunks == [para1, para2]
    assert all(len(c) <= 35 for c in chunks)


def test_chunk_text_falls_back_to_sentence_split_for_oversized_paragraph():
    sentence_a = "AAAA AAAA AAAA AAAA."
    sentence_b = "BBBB BBBB BBBB BBBB."
    sentence_c = "CCCC CCCC CCCC CCCC."
    paragraph = f"{sentence_a} {sentence_b} {sentence_c}"

    chunks = chunk_text(paragraph, max_chars=40)

    assert chunks == [sentence_a, sentence_b, sentence_c]


def test_chunk_text_ignores_blank_paragraphs():
    text = "Para one.\n\n\n\nPara two."

    chunks = chunk_text(text, max_chars=100)

    assert chunks == ["Para one.\n\nPara two."]


def _client_with_sequential_translations(translations: list[str]) -> DeepSeekClient:
    client = DeepSeekClient(api_key="test-key", client=MagicMock())
    results = [TranslationResult(translation=t, confidence=0.9) for t in translations]
    client.translate = MagicMock(side_effect=results)
    return client


def test_translate_long_text_joins_translated_chunks():
    client = _client_with_sequential_translations(["Uno.", "Dos."])

    result = translate_long_text(
        client,
        text="One.\n\nTwo.",
        target_language_name="European Spanish",
        max_chars=5,
    )

    assert result == "Uno.\n\nDos."


def test_translate_long_text_calls_translate_once_per_chunk_with_shared_context_and_glossary():
    para1 = "A" * 50
    para2 = "B" * 50
    text = f"{para1}\n\n{para2}"
    client = _client_with_sequential_translations(["Chunk 1 ES", "Chunk 2 ES"])
    terms = [GlossaryTerm(source="rover", target="rover")]

    translate_long_text(
        client,
        text=text,
        target_language_name="European Spanish",
        context="RTK Applications > Archaeology",
        glossary_terms=terms,
        max_chars=60,
    )

    assert client.translate.call_count == 2
    for call in client.translate.call_args_list:
        _, kwargs = call
        assert kwargs["target_language_name"] == "European Spanish"
        assert kwargs["context"] == "RTK Applications > Archaeology"
        assert kwargs["glossary_terms"] == terms
    first_call_args, _ = client.translate.call_args_list[0]
    assert first_call_args[0] == para1
    second_call_args, _ = client.translate.call_args_list[1]
    assert second_call_args[0] == para2


def test_translate_long_text_returns_single_translation_for_short_text():
    client = _client_with_sequential_translations(["Traducción única."])

    result = translate_long_text(
        client, text="Short text.", target_language_name="European Spanish"
    )

    assert result == "Traducción única."
    client.translate.assert_called_once()
