from app.translation.chunking import chunk_text


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
