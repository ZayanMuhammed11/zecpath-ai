"""
final_decision_ai/final_decision_engine.py

Day 52 Final Recommendation AI: a risk-adjusted final hiring decision
layer built on top of decision_ai's unified_scoring_pipeline() output.

This module performs NO event capture, NO video/audio analysis -- all
integrity and visual-behavior inputs are caller-supplied placeholders,
the same status as every upstream module producing them (see
integrity_ai/integrity_models.py and integrity_ai/integrity_scoring.py
for the precedent this module follows).

decision_confidence (on FinalDecision) is a NEW, distinctly-named,
variance-based metric. It is UNRELATED to and must not be confused
with decision_ai.UnifiedScore.confidence, which is a different,
round-presence-based metric computed from how many hiring rounds were
completed. The two concepts are named differently on purpose to avoid
collision/confusion (see DAY52_DECISIONS.md).

visual_behavior data, if supplied by the caller, is carried through
via VisualBehaviorContext for display only and never influences
adjusted_score or final_recommendation.

MODULE ISOLATION (hard rule): this module has ZERO imports from
decision_ai/, integrity_ai/, visual_behavior_ai/, interview_ai/,
technical_ai/, machine_test_ai/, screening_ai/, ats_engine/, or
scoring/. It only imports from final_decision_ai.final_decision_models
(intra-module) and utils.logger. All external data is accepted as
plain caller-supplied dicts/floats/strings.

DETERMINISM RULE (project-wide, non-negotiable): no use of the
`random` module anywhere in this file.
"""

from typing import Optional

from utils.logger import get_logger

from final_decision_ai.final_decision_models import (
    FinalDecision,
    RiskAdjustment,
    VisualBehaviorContext,
)

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Penalty points applied per integrity risk level. Keys must exactly
# match integrity_ai.get_integrity_risk_level()'s output values (see
# the attached integrity_scoring.py: "Low Risk", "Moderate Risk",
# "High Risk"). These are placeholder-reasonable constants, not
# derived from any real calibration data -- see DAY52_DECISIONS.md.
RISK_PENALTIES: dict[str, float] = {
    "Low Risk": 0.0,
    "Moderate Risk": 7.0,
    "High Risk": 15.0,
}


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------


def apply_risk_adjustment(
    base_final_score: float, integrity_risk_level: Optional[str] = None
) -> RiskAdjustment:
    """Determine whether, and how much of, a risk penalty applies.

    NO-FABRICATION RULE: this function must NEVER default
    ``integrity_risk_level`` to any assumed value when None is passed
    -- the absence of data must be explicitly represented
    (applied=False), not silently treated as "Low Risk" or any other
    default.

    Args:
        base_final_score: The unadjusted final score, included only
            for potential future use in the reason text; not required
            for the current penalty lookup.
        integrity_risk_level: The integrity risk level supplied by the
            caller, or None if no integrity data is available.

    Returns:
        A RiskAdjustment describing whether a penalty was applied and
        why.

    Raises:
        ValueError: If integrity_risk_level is supplied but is not a
            recognized key in RISK_PENALTIES.
    """
    if integrity_risk_level is None:
        return RiskAdjustment(
            applied=False,
            risk_level=None,
            penalty_points=0.0,
            reason="No integrity risk data supplied; no adjustment applied.",
        )

    if integrity_risk_level not in RISK_PENALTIES:
        valid_options = ", ".join(repr(k) for k in RISK_PENALTIES)
        raise ValueError(
            f"Invalid integrity_risk_level {integrity_risk_level!r}; "
            f"must be one of: {valid_options}."
        )

    penalty_points = RISK_PENALTIES[integrity_risk_level]

    if penalty_points == 0.0:
        reason = (
            f"Integrity risk level '{integrity_risk_level}' warranted no penalty."
        )
    else:
        reason = (
            f"Integrity risk level '{integrity_risk_level}' applied a "
            f"{penalty_points} point penalty."
        )

    return RiskAdjustment(
        applied=True,
        risk_level=integrity_risk_level,
        penalty_points=penalty_points,
        reason=reason,
    )


def calculate_decision_confidence(scores: list[float]) -> str:
    """Derive a variance-based confidence band from a list of scores.

    Mirrors the general idea of the manager-provided reference
    sample's calculate_decision_confidence() function (max(scores) -
    min(scores) as variance), but returns a band label instead of a
    raw float, fitting this module's string-based confidence
    convention.

    IMPORTANT: these bands are variance-based and independently
    defined -- they do NOT reuse decision_ai.get_confidence()'s
    round-presence-based high/medium/low semantics.

    In final_decision_pipeline(), this function is called with exactly
    two scores: [base_final_score, adjusted_score]. A small gap
    between them means the risk adjustment barely moved the score
    (high confidence in the decision); a large gap means the risk
    adjustment substantially changed the picture (low confidence).

    Args:
        scores: A list of scores to compare for variance. If empty or
            has fewer than 2 elements, there is no variance to
            measure.

    Returns:
        "high" if variance <= 10, "medium" if variance <= 30,
        otherwise "low". Returns "high" if fewer than 2 scores are
        given (nothing contradicts a single score).
    """
    if len(scores) < 2:
        return "high"

    variance = max(scores) - min(scores)

    if variance <= 10:
        return "high"
    elif variance <= 30:
        return "medium"
    else:
        return "low"


def build_visual_behavior_context(
    visual_behavior_score: Optional[float] = None,
    visual_behavior_level: Optional[str] = None,
) -> Optional[VisualBehaviorContext]:
    """Build a display-only visual behavior context, if any data was given.

    Args:
        visual_behavior_score: Caller-supplied visual behavior score
            (0-100), or None.
        visual_behavior_level: Caller-supplied visual behavior level
            label, or None.

    Returns:
        None if both arguments are None (no context object is
        fabricated). Otherwise a VisualBehaviorContext carrying the
        supplied values and a fixed explanatory note.
    """
    if visual_behavior_score is None and visual_behavior_level is None:
        return None

    return VisualBehaviorContext(
        visual_behavior_score=visual_behavior_score,
        level=visual_behavior_level,
        note=(
            "Visual behavior data is informational only and does not "
            "affect the adjusted score or final recommendation."
        ),
    )


def generate_final_reasoning(
    base_final_score: float,
    base_recommendation: str,
    risk_adjustment: RiskAdjustment,
    adjusted_score: float,
    final_recommendation: str,
) -> str:
    """Build deterministic, data-derived final-decision reasoning text.

    Args:
        base_final_score: The unadjusted score received from
            decision_ai.
        base_recommendation: The unadjusted recommendation received
            from decision_ai.
        risk_adjustment: The RiskAdjustment computed for this
            candidate.
        adjusted_score: The final, risk-adjusted score.
        final_recommendation: The recommendation derived from
            adjusted_score.

    Returns:
        A human-readable, fully deterministic reasoning string built
        from the actual values passed in. No LLM calls, no
        canned/templated strings unrelated to the actual computation.
    """
    base_sentence = (
        f"Received a base final score of {base_final_score:.2f} from "
        f"decision_ai with a base recommendation of '{base_recommendation}'."
    )

    adjustment_sentence = f" {risk_adjustment.reason}"

    adjusted_sentence = f" The resulting adjusted score is {adjusted_score:.2f}."

    final_sentence = f" Final recommendation: '{final_recommendation}'."

    if final_recommendation != base_recommendation:
        change_sentence = (
            f" This risk adjustment changed the recommendation from "
            f"'{base_recommendation}' to '{final_recommendation}'."
        )
    else:
        change_sentence = " The recommendation is unchanged by this adjustment."

    return (
        base_sentence
        + adjustment_sentence
        + adjusted_sentence
        + final_sentence
        + change_sentence
    )


def _get_recommendation_from_score(score: float) -> str:
    """Locally reimplement decision_ai's 75/55 recommendation thresholds.

    Deliberately duplicated here (three lines) rather than imported,
    per the module isolation hard rule -- this is a small threshold
    check, not a re-derivation of decision_ai's full engine.

    Args:
        score: A score (0-100).

    Returns:
        "selected" if score >= 75, "hold" if score >= 55, otherwise
        "rejected". Lowercase, exact same vocabulary and thresholds as
        decision_ai.get_recommendation().
    """
    if score >= 75:
        return "selected"
    elif score >= 55:
        return "hold"
    else:
        return "rejected"


def final_decision_pipeline(
    candidate_id: str,
    unified_score: dict,
    integrity_risk_level: Optional[str] = None,
    visual_behavior_score: Optional[float] = None,
    visual_behavior_level: Optional[str] = None,
) -> FinalDecision:
    """Single public entry point: run the full final-decision pipeline.

    Orchestrates apply_risk_adjustment -> adjusted_score computation ->
    final_recommendation derivation -> calculate_decision_confidence ->
    build_visual_behavior_context -> generate_final_reasoning ->
    assemble FinalDecision.

    Args:
        candidate_id: Identifier of the candidate being decided on.
        unified_score: Plain dict expected to contain at minimum the
            keys "final_score" (float) and "recommendation" (str) --
            mirroring decision_ai.UnifiedScore's field names, but
            received as a dict, not an imported model instance (module
            isolation).
        integrity_risk_level: Optional caller-supplied integrity risk
            level ("Low Risk" / "Moderate Risk" / "High Risk").
        visual_behavior_score: Optional caller-supplied visual
            behavior score (0-100), display-only.
        visual_behavior_level: Optional caller-supplied visual
            behavior level label, display-only.

    Returns:
        A fully populated FinalDecision model.

    Raises:
        ValueError: If "final_score" or "recommendation" is missing or
            None in unified_score, naming exactly which field(s) are
            missing.
    """
    logger.info(
        "Starting final decision pipeline for candidate=%s", candidate_id
    )

    missing = [
        key
        for key in ("final_score", "recommendation")
        if unified_score.get(key) is None
    ]
    if missing:
        raise ValueError(
            f"final_decision_pipeline received a unified_score dict "
            f"missing required field(s) {missing}: {unified_score!r}. "
            f"'final_score' and 'recommendation' must both be present "
            f"and non-None."
        )

    base_final_score = unified_score["final_score"]
    base_recommendation = unified_score["recommendation"]

    risk_adjustment = apply_risk_adjustment(base_final_score, integrity_risk_level)

    adjusted_score = max(
        0.0, round(base_final_score - risk_adjustment.penalty_points, 2)
    )

    final_recommendation = _get_recommendation_from_score(adjusted_score)

    decision_confidence = calculate_decision_confidence(
        [base_final_score, adjusted_score]
    )

    visual_behavior_context = build_visual_behavior_context(
        visual_behavior_score, visual_behavior_level
    )

    reasoning = generate_final_reasoning(
        base_final_score,
        base_recommendation,
        risk_adjustment,
        adjusted_score,
        final_recommendation,
    )

    result = FinalDecision(
        candidate_id=candidate_id,
        base_final_score=base_final_score,
        base_recommendation=base_recommendation,
        adjusted_score=adjusted_score,
        final_recommendation=final_recommendation,
        risk_adjustment=risk_adjustment,
        decision_confidence=decision_confidence,
        visual_behavior_context=visual_behavior_context,
        reasoning=reasoning,
    )

    logger.info(
        "Completed final decision pipeline for candidate=%s "
        "base_final_score=%s adjusted_score=%s final_recommendation=%s",
        candidate_id,
        base_final_score,
        adjusted_score,
        final_recommendation,
    )

    return result
