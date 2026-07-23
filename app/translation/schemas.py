"""Structured response schema for DeepSeek translation calls.

Matches the JSON contract defined in the project brief, section 11:
{"translation": "...", "confidence": 0.96, "issues": [...], "terminology_used": [...]}
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class TerminologyUsed(BaseModel):
    source: str
    target: str


class TranslationIssue(BaseModel):
    type: str
    description: str


class TranslationResult(BaseModel):
    translation: str
    confidence: float = Field(ge=0.0, le=1.0)
    issues: list[TranslationIssue] = Field(default_factory=list)
    terminology_used: list[TerminologyUsed] = Field(default_factory=list)


class ReviewResult(BaseModel):
    passed: bool
    issues: list[TranslationIssue] = Field(default_factory=list)


class TerminologyViolation(BaseModel):
    term: str
    expected: str
    found_as: str
    note: str = ""


class TerminologyValidationResult(BaseModel):
    compliant: bool
    violations: list[TerminologyViolation] = Field(default_factory=list)
