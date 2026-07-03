"""
interview_ai/confidence_models.py

Pydantic v2 models for the Day 36 confidence and behavioral signal
evaluation output. Part of the interview_ai module — fully isolated
from screening_ai/, ats_engine/, and scoring/.
"""

from pydantic import BaseModel, Field

from utils.logger import get_logger

logger = get_logger(__name__)


class ConfidenceSignals(BaseModel):
    """Raw per-signal sub-scores that feed into the confidence score.

    All four sub-scores are "positive" — a higher value always means
    a better (more confident) signal:
      - hesitation  = (1 - hesitation_density)
      - repetition  = (1 - repetition_ratio)
      - uncertainty = (1 - uncertainty_density)
      - pace        = pace quality score
    """

    hesitation: float = Field(ge=0, le=1, description="Hesitation sub-score (0.0–1.0); higher = less hesitation.")
    repetition: float = Field(ge=0, le=1, description="Repetition sub-score (0.0–1.0); higher = less repetition.")
    uncertainty: float = Field(ge=0, le=1, description="Uncertainty sub-score (0.0–1.0); higher = less uncertainty language.")
    pace: float = Field(ge=0, le=1, description="Speaking pace quality sub-score (0.0–1.0).")


class ConfidenceScore(BaseModel):
    """Aggregated confidence score derived from ConfidenceSignals."""

    confidence_score: float = Field(ge=0, le=100, description="Aggregated confidence score (0.0–100.0).")
    signals: ConfidenceSignals = Field(description="Per-signal sub-scores used to compute the confidence score.")


class SentimentResult(BaseModel):
    """Lexicon-based sentiment classification of an answer."""

    sentiment: str = Field(description="Overall sentiment classification: 'Positive', 'Neutral', or 'Negative'.")
    sentiment_score: float = Field(ge=0, le=1, description="Sentiment strength score (0.0–1.0).")


class BehaviorFlags(BaseModel):
    """Boolean behavior signal flags for a single answer.

    contradiction_detected uses surface linguistic markers only
    (contrast connectors such as "but"/"however") — it does NOT
    detect semantic contradiction. This is documented in
    DAY36_DECISIONS.md.
    """

    uncertainty_detected: bool = Field(description="True if uncertainty language was found in the answer.")
    contradiction_detected: bool = Field(description="True if a surface contrast marker ('but'/'however') was found in the answer.")


class ConfidenceBehaviorScore(BaseModel):
    """Top-level aggregated behavioral score for a single candidate answer."""

    confidence: ConfidenceScore = Field(description="Aggregated confidence score and signal breakdown.")
    sentiment: SentimentResult = Field(description="Lexicon-based sentiment classification.")
    behavior_flags: BehaviorFlags = Field(description="Boolean behavior signal flags.")
    stress_score: float = Field(ge=0, le=1, description="Stress indicator score (0.0–1.0); higher = less stress.")
    behavioral_score: float = Field(ge=0, le=100, description="Final aggregated behavioral score (0.0–100.0).")
