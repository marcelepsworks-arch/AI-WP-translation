"""Combines the mechanical QA checks (numbers, terminology, URLs) and
the DeepSeek Reviewer result (FASE 4.4) into one score and decision,
using the thresholds from the project brief, section 13:
>=95 auto-approve, 85-94 human review recommended, <85 automatic rejection.
"""
from __future__ import annotations

from pydantic import BaseModel

from app.qa.numerical_checker import NumericCheckResult
from app.qa.terminology_checker import TerminologyCheckResult
from app.qa.url_validator import UrlCheckResult

_NUMERIC_PENALTY = 40
_TERMINOLOGY_PENALTY = 25
_URL_PENALTY = 20
_REVIEW_PENALTY = 30


def _decide(score: int) -> str:
    if score >= 95:
        return "auto_approve"
    if score >= 85:
        return "human_review"
    return "reject"


class QAReport(BaseModel):
    numeric_passed: bool
    terminology_passed: bool
    url_passed: bool
    review_passed: bool
    score: int
    decision: str


def score_translation(
    numeric_result: NumericCheckResult,
    terminology_result: TerminologyCheckResult,
    url_result: UrlCheckResult,
    review_passed: bool,
) -> QAReport:
    score = 100
    if not numeric_result.passed:
        score -= _NUMERIC_PENALTY
    if not terminology_result.passed:
        score -= _TERMINOLOGY_PENALTY
    if not url_result.passed:
        score -= _URL_PENALTY
    if not review_passed:
        score -= _REVIEW_PENALTY
    score = max(0, score)

    return QAReport(
        numeric_passed=numeric_result.passed,
        terminology_passed=terminology_result.passed,
        url_passed=url_result.passed,
        review_passed=review_passed,
        score=score,
        decision=_decide(score),
    )
