"""Pydantic v2 data models for the Day 41 Unified Scoring Engine.

This module is fully self-contained and must not import from any other
project module (ATS, screening_ai, interview_ai, etc.). Any concept that
would normally be shared (such as RoleLevel) is deliberately duplicated
locally here rather than imported cross-module. See DAY41_DECISIONS.md for
the rationale.

Day 51 update: RoundScores extended with technical_score and
machine_test_score to support 5-round aggregation. See
DAY51_DECISIONS.md for the rationale (no other changes made to this
file — see that document).
"""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class RoleLevel(str, Enum):
    """Seniority level used to select role-based scoring weights.

    This enum is local to decision_ai/ and intentionally NOT imported from
    interview_ai/interview_models.py or any other module.
    """

    fresher = "fresher"
    mid = "mid"
    senior = "senior"


class RoundScores(BaseModel):
    """Raw scores (0-100) for each hiring round, computed elsewhere.

    Any field left as None indicates the candidate has not completed
    (or is not required to complete) that round.
    """

    ats_score: Optional[float] = Field(default=None, ge=0, le=100)
    screening_score: Optional[float] = Field(default=None, ge=0, le=100)
    hr_score: Optional[float] = Field(default=None, ge=0, le=100)
    technical_score: Optional[float] = Field(default=None, ge=0, le=100)
    machine_test_score: Optional[float] = Field(default=None, ge=0, le=100)


class RoundContribution(BaseModel):
    """The contribution of a single round to the final unified score."""

    round_name: str
    raw_score: float
    weight_used: float
    weighted_contribution: float


class UnifiedScoreBreakdown(BaseModel):
    """Full breakdown of how the final unified score was computed."""

    contributions: List[RoundContribution]
    rounds_included: List[str]
    rounds_missing: List[str]


class HiringFit(BaseModel):
    """Hiring-fit percentage and category derived from the final score."""

    hiring_fit_percentage: float = Field(ge=0, le=100)
    fit_category: str


class UnifiedScore(BaseModel):
    """Top-level result of the unified scoring pipeline for a candidate."""

    candidate_id: str
    final_score: float = Field(ge=0, le=100)
    recommendation: str
    confidence: str
    breakdown: UnifiedScoreBreakdown
    hiring_fit: HiringFit
    reasoning: str
    role_level_used: RoleLevel
