from app.qa.html_structure_checker import check_html_structure
from app.qa.numerical_checker import check_numbers
from app.qa.scoring import score_translation
from app.qa.terminology_checker import check_protected_terms
from app.qa.url_validator import check_urls


def test_score_translation_is_100_and_auto_approve_when_everything_passes():
    numeric = check_numbers("1 cm accuracy", "1 cm de precisión")
    terminology = check_protected_terms("RTK positioning", "posicionamiento RTK", ["RTK"])
    url = check_urls("no links here", "sin enlaces aquí")
    structure = check_html_structure("no markup", "sin marcado")

    report = score_translation(numeric, terminology, url, structure, review_passed=True)

    assert report.score == 100
    assert report.decision == "auto_approve"


def test_score_translation_rejects_the_brief_section_12_1_worked_example():
    # "1 cm accuracy" mistranslated as "2 cm de precisión" — brief's own FAIL example.
    numeric = check_numbers("1 cm accuracy", "2 cm de precisión")
    terminology = check_protected_terms("1 cm accuracy", "2 cm de precisión", [])
    url = check_urls("1 cm accuracy", "2 cm de precisión")
    structure = check_html_structure("no markup", "sin marcado")

    report = score_translation(numeric, terminology, url, structure, review_passed=True)

    assert report.numeric_passed is False
    assert report.score == 60
    assert report.decision == "reject"


def test_score_translation_flags_review_failure_alone_as_reject():
    numeric = check_numbers("text", "texto")
    terminology = check_protected_terms("text", "texto", [])
    url = check_urls("text", "texto")
    structure = check_html_structure("no markup", "sin marcado")

    report = score_translation(numeric, terminology, url, structure, review_passed=False)

    assert report.score == 70
    assert report.decision == "reject"


def test_score_translation_never_goes_below_zero_when_everything_fails():
    numeric = check_numbers("1 cm", "2 cm")
    terminology = check_protected_terms("RTK", "GPS", ["RTK"])
    url = check_urls("https://a.com", "https://b.com")
    structure = check_html_structure("no markup", "sin marcado")

    report = score_translation(numeric, terminology, url, structure, review_passed=False)

    assert report.score == 0
    assert report.decision == "reject"


def test_score_translation_penalises_a_lost_inline_tag():
    source = 'See the <a href="https://example.com/docs">manual</a>.'
    translated = "Consulta el manual."
    numeric = check_numbers(source, translated)
    terminology = check_protected_terms(source, translated, [])
    url = check_urls(source, translated)
    structure = check_html_structure(source, translated)

    report = score_translation(numeric, terminology, url, structure, review_passed=True)

    assert report.structure_passed is False
    assert report.decision == "reject"


def test_score_translation_still_auto_approves_when_lost_spacing_was_repaired():
    # A repaired space is not a defect in the delivered translation, so it must
    # not cost points -- the block ships correct. It is logged, not penalised.
    source = 'Use 2x <a href="https://example.com/k">Starter Kits</a> today.'
    translated = 'Usa 2x<a href="https://example.com/k">Kits Iniciales</a> hoy.'
    numeric = check_numbers(source, translated)
    terminology = check_protected_terms(source, translated, [])
    url = check_urls(source, translated)
    structure = check_html_structure(source, translated)

    report = score_translation(numeric, terminology, url, structure, review_passed=True)

    assert structure.repaired is True
    assert report.score == 100
    assert report.decision == "auto_approve"


def test_score_translation_decision_thresholds():
    from app.qa.scoring import _decide

    assert _decide(95) == "auto_approve"
    assert _decide(94) == "human_review"
    assert _decide(85) == "human_review"
    assert _decide(84) == "reject"
