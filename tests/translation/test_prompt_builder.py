from app.translation.prompt_builder import (
    GlossaryTerm,
    build_reviewer_system_prompt,
    build_system_prompt,
    build_terminology_validator_system_prompt,
)


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


def test_prompt_includes_spanish_acronym_article_rule_for_spanish_target():
    prompt = build_system_prompt("European Spanish")

    assert "artículos o determinantes obligatorios" in prompt
    assert "¿Por qué el RTK es esencial" in prompt
    assert "pasiva refleja" in prompt
    assert "no repetición" in prompt
    assert "sistema métrico" in prompt
    assert "verbos de acción nativos" in prompt.lower()
    assert "colocaciones léxicas naturales" in prompt.lower()


def test_prompt_omits_spanish_acronym_article_rule_for_non_spanish_target():
    prompt = build_system_prompt("French")

    assert "artículos o determinantes obligatorios" not in prompt
    assert "RTK es esencial" not in prompt


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


def test_reviewer_prompt_mentions_target_language():
    prompt = build_reviewer_system_prompt("European Spanish")

    assert "European Spanish" in prompt


def test_reviewer_prompt_lists_semantic_drift_categories():
    prompt = build_reviewer_system_prompt("European Spanish")

    assert "added" in prompt
    assert "removed" in prompt
    assert "degree of certainty" in prompt
    assert "terminology" in prompt


def test_reviewer_prompt_specifies_response_shape():
    prompt = build_reviewer_system_prompt("European Spanish")

    assert '"passed"' in prompt
    assert '"issues"' in prompt


def test_terminology_validator_prompt_mentions_target_language():
    prompt = build_terminology_validator_system_prompt("European Spanish")

    assert "European Spanish" in prompt


def test_terminology_validator_prompt_specifies_response_shape():
    prompt = build_terminology_validator_system_prompt("European Spanish")

    assert '"compliant"' in prompt
    assert '"violations"' in prompt


def test_terminology_validator_prompt_includes_glossary_when_given():
    terms = [GlossaryTerm(source="rover", target="rover")]

    prompt = build_terminology_validator_system_prompt("European Spanish", terms)

    assert "MANDATORY GLOSSARY" in prompt
    assert "rover -> rover" in prompt


def test_terminology_validator_prompt_has_no_glossary_section_when_no_terms_given():
    prompt = build_terminology_validator_system_prompt("European Spanish")

    assert "MANDATORY GLOSSARY" not in prompt
