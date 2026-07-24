from app.qa.terminology_checker import check_protected_terms


def test_check_protected_terms_passes_when_all_present_terms_survive():
    result = check_protected_terms(
        source_text="The ZED-F9P module uses RTK positioning.",
        translated_text="El módulo ZED-F9P usa posicionamiento RTK.",
        protected_terms=["ZED-F9P", "RTK"],
    )

    assert result.passed is True
    assert result.missing_terms == []


def test_check_protected_terms_flags_a_term_dropped_in_translation():
    result = check_protected_terms(
        source_text="The ZED-F9P module uses RTK positioning.",
        translated_text="El módulo usa posicionamiento por satélite.",
        protected_terms=["ZED-F9P", "RTK"],
    )

    assert result.passed is False
    assert set(result.missing_terms) == {"ZED-F9P", "RTK"}


def test_check_protected_terms_ignores_terms_not_present_in_source():
    result = check_protected_terms(
        source_text="The receiver connects over NTRIP.",
        translated_text="El receptor se conecta mediante NTRIP.",
        protected_terms=["ZED-F9P"],  # not in source at all
    )

    assert result.passed is True
    assert result.missing_terms == []


def test_check_protected_terms_is_case_sensitive_on_the_translation_side():
    # Product codes/acronyms must survive with their exact casing.
    result = check_protected_terms(
        source_text="Uses the ZED-F9P receiver.",
        translated_text="Usa el receptor zed-f9p.",
        protected_terms=["ZED-F9P"],
    )

    assert result.passed is False
    assert result.missing_terms == ["ZED-F9P"]
