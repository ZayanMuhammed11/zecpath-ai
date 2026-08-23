"""
technical_ai/technical_scoring_models.py

Pydantic v2 models for the Day 47 Technical Interview scoring engine
output. Part of the technical_ai module -- fully isolated from
interview_ai/, screening_ai/, ats_engine/, and scoring/.

Mirrors the docstring and Field-description conventions of
interview_ai/hr_scoring_models.py, adapted for the technical-answer
scoring domain. See technical_ai/DAY47_DECISIONS.md for design
rationale.
"""

from pydantic import BaseModel, Field

from utils.logger import get_logger

logger = get_logger(__name__)


class TechnicalAnswerScoreBreakdown(BaseModel):
    """Per-dimension breakdown of the sub-scores used to compute a
    technical answer's final score.

    All four sub-scores represent a normalised 0.0-1.0 range.
    """

    accuracy: float = Field(
        ge=0,
        le=1,
        description=(
            "Caller-supplied correctness sub-score (0.0-1.0). This "
            "engine does not classify correctness itself -- see module "
            "docstring."
        ),
    )
    depth: float = Field(
        ge=0, le=1, description="Depth-of-explanation sub-score (0.0-1.0)."
    )
    logic: float = Field(
        ge=0, le=1, description="Logical reasoning structure sub-score (0.0-1.0)."
    )
    real_world: float = Field(
        ge=0, le=1, description="Real-world applicability sub-score (0.0-1.0)."
    )


class TechnicalAnswerScore(BaseModel):
    """Top-level technical score for a single candidate answer.

    Captures the aggregated 0-100 final score and the per-dimension
    breakdown that produced it.
    """

    question_id: str = Field(
        description="Identifier of the question this score corresponds to."
    )
    skill_domain: str = Field(
        description=(
            "TechnicalSkillDomain value this question belongs to, stored "
            "as plain str for JSON/dict portability."
        )
    )
    final_score: float = Field(
        ge=0, le=100, description="Aggregated technical answer score (0.0-100.0), rounded to 2 d.p."
    )
    breakdown: TechnicalAnswerScoreBreakdown = Field(
        description="Per-dimension sub-scores used to compute the final score."
    )


class TechnicalInterviewScore(BaseModel):
    """Top-level aggregated technical score for an entire interview."""

    technical_score: float = Field(
        ge=0,
        le=100,
        description="Mean of all scored answers' final_score.",
    )
    decision: str = Field(
        description=(
            "Technical-track hiring signal: Strong Technical Fit | "
            "Moderate Technical Fit | Weak Technical Fit. Deliberately "
            "distinct wording from the HR interview engine's Strong "
            "Hire/Consider/Reject labels, even though numeric thresholds "
            "are the same (75/55) -- this is intentional, to avoid "
            "presenting two differently-scoped 'Reject' labels to a "
            "recruiter. See DAY47_DECISIONS.md."
        )
    )
    scored_answers: list[TechnicalAnswerScore] = Field(
        description="Per-answer scores that make up this interview's aggregate."
    )
    skill_breakdown: dict[str, float] = Field(
        description=(
            "Mean final_score per skill_domain value, computed only "
            "over scored_answers actually present for that domain."
        )
    )
