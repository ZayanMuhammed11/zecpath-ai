"""
hiring_report_ai/hiring_report_models.py

Pydantic v2 data models for the Day 53 Hiring Intelligence Report
(pure compilation layer over every existing scoring module's output).

MODULE ISOLATION: this file has zero imports from decision_ai/,
final_decision_ai/, integrity_ai/, visual_behavior_ai/, interview_ai/,
technical_ai/, machine_test_ai/, screening_ai/, ats_engine/, or
scoring/. All external data (ATS results, unified scores, interview
summaries, etc.) is received elsewhere in this module as plain
dicts, never as imported Pydantic model instances from other modules.
See DAY53_DECISIONS.md for rationale.
"""

from typing import Optional

from pydantic import BaseModel, Field


class RoundSummary(BaseModel):
    """Compiled summary of a single hiring round for report display.

    round_name is a plain string (one of: "ats", "screening",
    "hr_interview", "technical", "machine_test") — deliberately not an
    enum, since this module does not own any of these concepts.
    """

    round_name: str
    score: Optional[float] = Field(default=None, ge=0, le=100)
    label: Optional[str] = None
    included: bool


class BehavioralIntegrityNotes(BaseModel):
    """Passthrough display section for visual-behavior and integrity
    signals. Never influences the authoritative recommendation.
    """

    visual_behavior_score: Optional[float] = Field(default=None, ge=0, le=100)
    visual_behavior_level: Optional[str] = None
    visual_behavior_note: str
    integrity_score: Optional[float] = Field(default=None, ge=0, le=100)
    integrity_risk_level: Optional[str] = None
    integrity_warnings: list[str] = Field(default_factory=list)


class HighlightsSection(BaseModel):
    """Direct passthrough of InterviewSummaryHighlights values, when
    supplied. Empty lists otherwise — never fabricated.
    """

    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    inconsistencies: list[str] = Field(default_factory=list)


class AuthoritativeRecommendation(BaseModel):
    """The single recommendation a recruiter should act on, selected
    (not derived) from existing downstream module outputs.
    """

    recommendation: Optional[str] = None
    source: str
    rationale: str


class HiringIntelligenceReport(BaseModel):
    """Top-level recruiter-facing hiring intelligence report for a
    single candidate, compiled from every existing scoring module's
    output.
    """

    candidate_id: str
    job_title: Optional[str] = None
    rounds: list[RoundSummary]
    authoritative_recommendation: AuthoritativeRecommendation
    supporting_labels_note: str
    highlights: HighlightsSection
    behavioral_integrity_notes: BehavioralIntegrityNotes
    report_text: str
