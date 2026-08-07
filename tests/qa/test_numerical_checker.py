from app.qa.numerical_checker import check_numbers, extract_numbers


def test_extract_numbers_finds_integers_and_decimals():
    assert extract_numbers("The tolerance is 0.5 cm over 10 km.") == ["0.5", "10"]


def test_check_numbers_passes_when_source_example_from_brief_matches():
    # Brief section 12.1 worked example.
    result = check_numbers("1 cm accuracy", "1 cm de precisión")

    assert result.passed is True


def test_check_numbers_fails_when_source_example_from_brief_is_altered():
    # Brief section 12.1: "Si apareix 2 cm: Resultat: FAIL"
    result = check_numbers("1 cm accuracy", "2 cm de precisión")

    assert result.passed is False
    assert result.source_numbers == ["1"]
    assert result.translated_numbers == ["2"]


def test_check_numbers_tolerates_comma_decimal_separator_in_spanish():
    result = check_numbers("The tolerance is 0.5 cm.", "La tolerancia es de 0,5 cm.")

    assert result.passed is True


def test_check_numbers_passes_when_a_range_is_preserved():
    result = check_numbers("Effective up to 5-10 km.", "Efectivo hasta 5-10 km.")

    assert result.passed is True


def test_check_numbers_ignores_currency_symbol_differences():
    result = check_numbers("The receiver costs $99.", "El receptor cuesta 99€.")

    assert result.passed is True


def test_check_numbers_tolerates_legitimate_acronym_repetition():
    # Real case found 2026-08-06 on precision-gnss.com: translator spells
    # out an acronym in parentheses, repeating the number — not an error.
    result = check_numbers(
        "7-DoF Manipulation system",
        "sistema de manipulación de 7 grados de libertad (7-DoF)",
    )

    assert result.passed is True


def test_check_numbers_still_fails_when_a_number_is_genuinely_dropped():
    result = check_numbers("5 satellites in view, 3 fixed.", "5 satélites a la vista, 5 fijos.")

    assert result.passed is False
