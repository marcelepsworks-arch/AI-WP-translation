from app.translation.prompt_builder import GlossaryTerm, build_system_prompt


def test_prompt_mentions_target_language():
    prompt = build_system_prompt("European Spanish")

    assert "European Spanish" in prompt


def test_prompt_includes_core_fidelity_rules():
    prompt = build_system_prompt("European Spanish")

    assert "Preserve the exact meaning of the source" in prompt
    assert "Preserve numerical values and units exactly" in prompt
    assert "Never invent information" in prompt
    assert "Return valid structured JSON" in prompt


def test_prompt_includes_must_not_rules():
    prompt = build_system_prompt("European Spanish")

    assert "simplify technical language" in prompt
    assert "translate protected product names" in prompt


def test_prompt_has_no_glossary_section_when_no_terms_given():
    prompt = build_system_prompt("European Spanish")

    assert "MANDATORY GLOSSARY" not in prompt


def test_prompt_includes_glossary_terms_when_given():
    terms = [
        GlossaryTerm(source="base station", target="estación base", notes="GNSS/RTK context"),
        GlossaryTerm(source="rover", target="rover"),
    ]

    prompt = build_system_prompt("European Spanish", terms)

    assert "MANDATORY GLOSSARY" in prompt
    assert "base station -> estación base" in prompt
    assert "GNSS/RTK context" in prompt
    assert "rover -> rover" in prompt
