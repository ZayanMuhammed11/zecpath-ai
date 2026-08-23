"""
visual_behavior_ai/visual_behavior_scoring.py

Day 48 visual behavior scoring engine. Combines four caller-supplied
sub-signals (gaze_stability, head_stability, facial_engagement,
attention_consistency) into a single weighted visual_behavior_score.

IMPORTANT: this module contains NO video/webcam capture logic and NO
computer-vision logic. Every numeric input to every function in this
module is 100% CALLER-SUPPLIED. No signal-extraction pipeline exists
anywhere in this codebase yet -- video interview infrastructure is
unbuilt. These are placeholder inputs pending a future video-capture
implementation, not signals this code derives itself.

Part of the visual_behavior_ai module -- fully isolated from
interview_ai/, technical_ai/, screening_ai/, ats_engine/, scoring/,
and decision_ai/. Only imports from
visual_behavior_ai.visual_behavior_models (intra-module, permitted).
This module is deliberately NOT wired into decision_ai/, any summary
generator, or any other scoring system.

DETERMINISM RULE (non-negotiable, project-wide): no use of the
`random` module anywhere in this file.
"""

from utils.logger import get_logger

from visual_behavior_ai.visual_behavior_models import (
    VisualBehaviorScore,
    VisualBehaviorSignals,
)

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Weights
# ---------------------------------------------------------------------------

DEFAULT_WEIGHTS: dict[str, float] = {
    "gaze_stability": 0.30,
    "head_stability": 0.20,
    "facial_engagement": 0.30,
    "attention_consistency": 0.20,
}
assert sum(DEFAULT_WEIGHTS.values()) == 1.0

# Same order as DEFAULT_WEIGHTS.
REQUIRED_SIGNAL_KEYS: tuple[str, ...] = (
    "gaze_stability",
    "head_stability",
    "facial_engagement",
    "attention_consistency",
)


# ---------------------------------------------------------------------------
# Public scoring functions
# ---------------------------------------------------------------------------


def calculate_visual_behavior_score(
    signals: dict[str, float],
    weights: dict[str, float] = DEFAULT_WEIGHTS,
) -> VisualBehaviorScore:
    """Score a set of caller-supplied visual behavior signals.

    All four signal values in ``signals`` are CALLER-SUPPLIED
    placeholders (see module docstring) -- this function performs no
    signal extraction of its own.

    DAY 48 VALIDATION PRECEDENT (mirrored from
    technical_ai.technical_scoring_engine.technical_scoring_pipeline):
    required keys are explicitly validated as present and non-None
    BEFORE constructing the signals model, so a missing key surfaces
    as a clear, diagnosable ValueError naming exactly which field(s)
    are missing, rather than a raw error deep inside Pydantic
    validation. Out-of-range values (outside [0.0, 1.0]) are NOT
    manually checked here -- constructing ``VisualBehaviorSignals``
    naturally enforces that bound via its Field constraints, and that
    validation error is allowed to propagate unmodified.

    Args:
        signals: Dict of caller-supplied signal values, keyed by the
            four names in REQUIRED_SIGNAL_KEYS.
        weights: Per-signal weights to apply, keyed by the same four
            names. Defaults to DEFAULT_WEIGHTS.

    Returns:
        A fully populated VisualBehaviorScore.

    Raises:
        ValueError: If any of REQUIRED_SIGNAL_KEYS is missing from or
            None in ``signals``.
        pydantic.ValidationError: If any present signal value falls
            outside [0.0, 1.0].
    """
    logger.debug("calculate_visual_behavior_score called with signals=%r", signals)

    missing = [k for k in REQUIRED_SIGNAL_KEYS if signals.get(k) is None]
    if missing:
        raise ValueError(
            f"calculate_visual_behavior_score received a signals dict "
            f"missing required field(s) {missing}: {signals!r}. "
            f"gaze_stability, head_stability, facial_engagement, and "
            f"attention_consistency must all be present and non-None."
        )

    signals_model = VisualBehaviorSignals(
        gaze_stability=signals["gaze_stability"],
        head_stability=signals["head_stability"],
        facial_engagement=signals["facial_engagement"],
        attention_consistency=signals["attention_consistency"],
    )

    visual_behavior_score = round(
        sum(
            getattr(signals_model, k) * weights[k] for k in REQUIRED_SIGNAL_KEYS
        )
        * 100,
        2,
    )

    level = get_visual_behavior_level(visual_behavior_score)

    logger.info(
        "calculate_visual_behavior_score visual_behavior_score=%.2f level=%s",
        visual_behavior_score,
        level,
    )

    return VisualBehaviorScore(
        visual_behavior_score=visual_behavior_score,
        level=level,
        signals=signals_model,
    )


def get_visual_behavior_level(score: float) -> str:
    """Map a visual behavior score to an engagement level label.

    This labeling is DELIBERATELY worded differently from every other
    decision-band function in the platform (HR's Strong Hire/Consider/
    Reject; technical_ai's Strong/Moderate/Weak Technical Fit), with
    independently scoped thresholds, to avoid adding a confusable
    fifth label-family -- a conscious mitigation of this project's
    known "three-way score-label divergence" backlog concern, not an
    oversight.

    Args:
        score: Aggregate visual behavior score (0.0-100.0).

    Returns:
        "Highly Engaged" if score >= 80, "Engaged" if score >= 60,
        "Variable Engagement" if score >= 40, otherwise
        "Low Engagement".
    """
    if score >= 80:
        return "Highly Engaged"
    if score >= 60:
        return "Engaged"
    if score >= 40:
        return "Variable Engagement"
    return "Low Engagement"
