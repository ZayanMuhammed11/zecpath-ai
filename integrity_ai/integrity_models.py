"""
integrity_ai/integrity_models.py

Pydantic v2 models for the Day 49 integrity (exam-integrity /
anti-cheating) signal-to-risk-score mapping.

IMPORTANT: this module contains NO browser tab-switch detection, NO
screen focus tracking, NO audio voice detection, and NO gaze tracking
logic. Every field on ``IntegrityEvents`` is a CALLER-SUPPLIED
placeholder int representing a raw event count. No event-capture
pipeline exists anywhere in this codebase yet -- browser/audio/video
interview-monitoring infrastructure is unbuilt. These models simply
define the shape of that future signal, they do not derive it.

Part of the integrity_ai module -- fully isolated from interview_ai/,
technical_ai/, screening_ai/, ats_engine/, scoring/, decision_ai/, and
visual_behavior_ai/. This file has zero imports from any other project
module.
"""

from pydantic import BaseModel, Field

from utils.logger import get_logger

logger = get_logger(__name__)


class IntegrityEvents(BaseModel):
    """Raw per-event caller-supplied counts collected over an interview
    session.

    All four fields are RAW EVENT COUNTS -- caller-supplied
    placeholders, not derived by this code. No event-capture pipeline
    exists in this codebase yet, pending a future browser/audio/video
    monitoring implementation.
    """

    tab_switch_count: int = Field(
        ge=0,
        description="Raw count of browser tab-switch events during the session; caller-supplied placeholder.",
    )
    focus_loss_count: int = Field(
        ge=0,
        description="Raw count of screen/window focus-loss events during the session; caller-supplied placeholder.",
    )
    external_voice_count: int = Field(
        ge=0,
        description="Raw count of detected external-voice events during the session; caller-supplied placeholder.",
    )
    gaze_deviation_count: int = Field(
        ge=0,
        description="Raw count of gaze-deviation events during the session; caller-supplied placeholder.",
    )


class IntegritySignals(BaseModel):
    """Normalized per-signal sub-scores derived from ``IntegrityEvents``.

    All four sub-scores are "positive" -- a higher value always means
    LESS risky (i.e. these are inverted sub-scores relative to the raw
    event counts), the same "positive" convention used by
    interview_ai.ConfidenceSignals and
    visual_behavior_ai.VisualBehaviorSignals.
    """

    tab_switch_signal: float = Field(
        ge=0,
        le=1,
        description="Normalized tab-switch risk signal (0.0-1.0); higher = less risky (fewer tab switches).",
    )
    focus_loss_signal: float = Field(
        ge=0,
        le=1,
        description="Normalized focus-loss risk signal (0.0-1.0); higher = less risky (fewer focus-loss events).",
    )
    external_voice_signal: float = Field(
        ge=0,
        le=1,
        description="Normalized external-voice risk signal (0.0-1.0); higher = less risky (fewer external-voice events).",
    )
    gaze_deviation_signal: float = Field(
        ge=0,
        le=1,
        description="Normalized gaze-deviation risk signal (0.0-1.0); higher = less risky (fewer gaze-deviation events).",
    )


class IntegrityScore(BaseModel):
    """Aggregated integrity/risk score derived from ``IntegrityEvents``
    and ``IntegritySignals``.

    All input event counts are caller-supplied placeholders (see
    module docstring); this model only represents the resulting
    aggregation.
    """

    integrity_score: float = Field(
        ge=0, le=100, description="Aggregated integrity score (0.0-100.0); higher = less risky."
    )
    risk_level: str = Field(
        description="Risk level label derived from integrity_score: 'Low Risk', 'Moderate Risk', or 'High Risk'."
    )
    events: IntegrityEvents = Field(
        description="Raw caller-supplied event counts."
    )
    signals: IntegritySignals = Field(
        description="Normalized per-signal sub-scores derived from events."
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Deterministic warning messages triggered by individual signal thresholds.",
    )
