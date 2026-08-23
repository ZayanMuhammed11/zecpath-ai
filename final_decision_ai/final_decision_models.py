"""
final_decision_ai/final_decision_models.py

Pydantic v2 data models for the Day 52 Final Recommendation AI
(risk-adjusted final hiring decision layer).

MODULE ISOLATION: this file has zero imports from decision_ai/,
integrity_ai/, visual_behavior_ai/, interview_ai/, technical_ai/,
machine_test_ai/, screening_ai/, ats_engine/, or scoring/. All
external data (unified score, integrity risk level, visual behavior
score/level) is received elsewhere in this module as plain
dicts/floats/strings, never as imported Pydantic model instances from
other modules.
"""

from typing import Optional

from pydantic import BaseModel, Field


class RiskAdjustment(BaseModel):
    """Represents whether, and how, an integrity-risk-based penalty was
    applied to a base final score.

    NO-FABRICATION RULE: ``applied`` is True only if a real
    ``integrity_risk_level`` was supplied and used. When no integrity
    risk data is supplied, this must be explicitly represented as
    ``applied=False`` -- never silently defaulted to "Low Risk" or any
    other assumed value.
    """

    applied: bool
    risk_level: Optional[str] = None
    penalty_points: float = Field(ge=0)
    reason: str


class VisualBehaviorContext(BaseModel):
    """Purely informational passthrough of visual-behavior data.

    NEVER affects scoring. If supplied, this data is carried through
    for display only and has zero effect on adjusted_score or
    final_recommendation.
    """

    visual_behavior_score: Optional[float] = Field(default=None, ge=0, le=100)
    level: Optional[str] = None
    note: str


class FinalDecision(BaseModel):
    """Top-level result of the Day 52 risk-adjusted final decision
    pipeline for a candidate.
    """

    candidate_id: str
    base_final_score: float = Field(ge=0, le=100)
    base_recommendation: str
    adjusted_score: float = Field(ge=0, le=100)
    final_recommendation: str
    risk_adjustment: RiskAdjustment
    decision_confidence: str
    visual_behavior_context: Optional[VisualBehaviorContext] = None
    reasoning: str
