"""
interview_ai/summary_models.py

Pydantic v2 models for the Day 39 Interview Summary Generator output.
Part of the interview_ai module — fully isolated from screening_ai/,
ats_engine/, and scoring/.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from utils.logger import get_logger

logger = get_logger(__name__)


class CulturalFitLevel(str, Enum):
    """Qualitative banding for the cultural-fit indicator."""

    good = "good"
    moderate = "moderate"
    low = "low"


class InterviewSummaryHighlights(BaseModel):
    """Bullet-point highlights extracted from an interview's scoring outputs.

    Any of the four lists may legitimately be empty — no placeholder
    strings are ever forced into a list to guarantee a minimum length.
    """

    strengths: list[str] = Field(default_factory=list, description="Positive highlights drawn from HR, communication, and behavioral scores.")
    weaknesses: list[str] = Field(default_factory=list, description="Weak points drawn from HR, communication, and behavioral scores.")
    risks: list[str] = Field(default_factory=list, description="Risk flags drawn from confidence and stress signals.")
    inconsistencies: list[str] = Field(default_factory=list, description="Scoped inconsistency notes; see extract_inconsistencies docstring for capability limits.")


class CulturalFitIndicator(BaseModel):
    """Graduated cultural-fit score derived from existing upstream signals.

    This is NOT keyword matching — it is computed from the
    contradiction flag and consistency sub-scores already produced by
    Day 36/37 modules.
    """

    level: CulturalFitLevel = Field(description="Qualitative cultural-fit banding.")
    score: float = Field(ge=0, le=1, description="Graduated cultural-fit score in [0, 1], rounded to 4 d.p.")
    rationale: str = Field(description="Short human-readable explanation of which factors applied, e.g. 'no contradictions detected; consistency high'.")


class InterviewSummaryComposite(BaseModel):
    """Display/recruiter-summary composite score for a single interview.

    IMPORTANT: This is a display/recruiter-summary composite ONLY. It
    is NOT the platform's future formal cross-round Decision Service
    aggregation, which will separately combine ATS + Aptitude +
    Machine Test scores. This composite exists solely to fulfill the
    Day 39 "summarize overall HR performance" deliverable and must not
    be treated as, or later silently promoted into, that future
    cross-round aggregation.
    """

    overall_score: float = Field(ge=0, le=100, description="Weighted composite of hr_score (0.4), communication_score (0.3), and behavioral_score (0.3), rounded to 2 d.p.")
    decision: str = Field(description="Hiring decision derived from overall_score: Strong Hire | Consider | Reject.")
    hr_score: float = Field(description="hr_score carried through from the Day 37 HR interview scoring output.")
    communication_score: float = Field(description="communication_score carried through from the Day 39-consumed communication output.")
    behavioral_score: float = Field(description="behavioral_score carried through from the Day 36 confidence/behavior output.")
    aptitude_score: Optional[float] = Field(default=None, description="aptitude_score carried through for display only. NEVER included in the overall_score weighted calculation.")


class InterviewSummary(BaseModel):
    """Top-level recruiter-facing interview summary."""

    candidate_id: str = Field(description="Identifier of the candidate this summary belongs to.")
    composite: InterviewSummaryComposite = Field(description="Display composite score and decision.")
    highlights: InterviewSummaryHighlights = Field(description="Strengths, weaknesses, risks, and inconsistencies.")
    cultural_fit: CulturalFitIndicator = Field(description="Graduated cultural-fit indicator.")
    aptitude_score: Optional[float] = Field(default=None, description="Reported for visibility only; not part of composite weighting.")
    natural_language_summary: str = Field(description="Deterministic, template-generated narrative summary.")
