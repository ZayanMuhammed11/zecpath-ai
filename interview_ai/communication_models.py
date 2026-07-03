"""
interview_ai/communication_models.py

Pydantic v2 models for the communication skill evaluation output.
Part of the interview_ai module — fully isolated from screening_ai/.
"""

from pydantic import BaseModel, Field

from utils.logger import get_logger

logger = get_logger(__name__)


class CommunicationScoreBreakdown(BaseModel):
    """Per-dimension breakdown of communication sub-scores and the filler-word deduction.

    All sub-scores represent a normalised 0.0–1.0 range.
    filler_penalty is a deduction (not a sub-score) capped at 0.5.
    """

    fluency: float = Field(ge=0, le=1, description="Fluency sub-score (0.0–1.0).")
    grammar: float = Field(ge=0, le=1, description="Grammar sub-score (0.0–1.0).")
    vocabulary: float = Field(ge=0, le=1, description="Vocabulary richness sub-score (0.0–1.0).")
    clarity: float = Field(ge=0, le=1, description="Clarity sub-score (0.0–1.0).")
    structure: float = Field(ge=0, le=1, description="Structural quality sub-score (0.0–1.0).")
    filler_penalty: float = Field(
        ge=0, le=0.5, description="Filler-word deduction applied to the weighted score (0.0–0.5)."
    )


class CommunicationScore(BaseModel):
    """Top-level communication quality score for a single candidate answer.

    Captures the aggregated 0–100 score, its qualitative level label,
    the per-dimension breakdown, and the total word count of the evaluated text.
    """

    communication_score: float = Field(
        ge=0, le=100, description="Aggregated communication score (0.0–100.0), rounded to 2 d.p."
    )
    level: str = Field(
        description="Qualitative level derived from the score: Excellent | Good | Average | Poor."
    )
    breakdown: CommunicationScoreBreakdown = Field(
        description="Per-dimension scores and filler penalty used to compute the final score."
    )
    word_count: int = Field(description="Total word count of the evaluated answer text.")
