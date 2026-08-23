"""
visual_behavior_ai/visual_behavior_models.py

Pydantic v2 models for the Day 48 visual behavior scoring output.

IMPORTANT: this module contains NO video/webcam capture logic and NO
computer-vision logic. Every field on ``VisualBehaviorSignals`` is a
CALLER-SUPPLIED placeholder float. No signal-extraction pipeline
exists anywhere in this codebase yet -- video interview infrastructure
is unbuilt. These models simply define the shape of that future
signal, they do not derive it.

Part of the visual_behavior_ai module -- fully isolated from
interview_ai/, technical_ai/, screening_ai/, ats_engine/, scoring/,
and decision_ai/. This file has zero imports from any other project
module.
"""

from pydantic import BaseModel, Field

from utils.logger import get_logger

logger = get_logger(__name__)


class VisualBehaviorSignals(BaseModel):
    """Raw per-signal caller-supplied inputs that feed into the visual
    behavior score.

    All four sub-scores are "positive" -- a higher value always means
    a better (more engaged) signal. Every field is a CALLER-SUPPLIED
    placeholder: no signal-extraction logic exists in this codebase,
    pending a future video-capture implementation.
    """

    gaze_stability: float = Field(
        ge=0,
        le=1,
        description="Stability/consistency of eye gaze on screen (0.0–1.0); higher = more stable.",
    )
    head_stability: float = Field(
        ge=0,
        le=1,
        description="Stability of head position/movement (0.0–1.0); higher = less erratic movement.",
    )
    facial_engagement: float = Field(
        ge=0,
        le=1,
        description="Facial engagement/attentiveness signal (0.0–1.0); higher = more engaged.",
    )
    attention_consistency: float = Field(
        ge=0,
        le=1,
        description="Consistency of sustained attention over the session (0.0–1.0); higher = more consistent.",
    )


class VisualBehaviorScore(BaseModel):
    """Aggregated visual behavior score derived from
    ``VisualBehaviorSignals``.

    All input signals are caller-supplied placeholders (see module
    docstring); this model only represents the resulting aggregation.
    """

    visual_behavior_score: float = Field(
        ge=0, le=100, description="Aggregated visual behavior score (0.0–100.0)."
    )
    level: str = Field(
        description="Engagement level label derived from visual_behavior_score."
    )
    signals: VisualBehaviorSignals = Field(
        description="Per-signal inputs used to compute the score."
    )
