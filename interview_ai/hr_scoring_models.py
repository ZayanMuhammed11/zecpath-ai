"""
interview_ai/hr_scoring_models.py

Pydantic v2 models for the Day 37 HR interview scoring engine output.
Part of the interview_ai module — fully isolated from screening_ai/,
ats_engine/, and scoring/.
"""

from pydantic import BaseModel, Field

from utils.logger import get_logger

logger = get_logger(__name__)


class HRAnswerScoreBreakdown(BaseModel):
    """Per-dimension breakdown of the sub-scores used to compute an
    HR answer's final score.

    All four sub-scores represent a normalised 0.0–1.0 range.
    """

    relevance: float = Field(ge=0, le=1, description="Relevance sub-score (0.0–1.0).")
    communication: float = Field(ge=0, le=1, description="Communication sub-score (0.0–1.0).")
    confidence: float = Field(ge=0, le=1, description="Confidence sub-score (0.0–1.0).")
    consistency: float = Field(ge=0, le=1, description="Consistency sub-score (0.0–1.0).")


class HRAnswerScore(BaseModel):
    """Top-level HR score for a single candidate answer.

    Captures the aggregated 0–100 final score and the per-dimension
    breakdown that produced it.
    """

    question_id: str = Field(description="Identifier of the question this score corresponds to.")
    final_score: float = Field(ge=0, le=100, description="Aggregated HR answer score (0.0–100.0), rounded to 2 d.p.")
    breakdown: HRAnswerScoreBreakdown = Field(description="Per-dimension sub-scores used to compute the final score.")


class HRInterviewScore(BaseModel):
    """Top-level aggregated HR score for an entire interview.

    hr_score is the arithmetic mean of all HRAnswerScore.final_score
    values, which length-normalizes the aggregate across interviews
    with differing numbers of questions.
    """

    hr_score: float = Field(ge=0, le=100, description="Aggregated interview HR score (0.0–100.0), mean of all answer final_score values.")
    decision: str = Field(description="Hiring decision derived from hr_score: Strong Hire | Consider | Reject.")
    scored_answers: list[HRAnswerScore] = Field(description="Per-answer scores that make up this interview's aggregate.")
