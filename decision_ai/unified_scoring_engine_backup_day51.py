"""Deterministic unified scoring engine for Day 41.

Combines ATS, screening, and HR interview round scores into a single
unified hiring score with role-based weighting, missing-round
redistribution, hiring-fit categorization, a recommendation, a confidence
rating, and deterministic (non-LLM) reasoning text.

No Redis, no LLM calls, no randomness — pure deterministic computation only.
"""

# NOTE: utils.logger is not available to this self-contained module. A
# minimal local logger is used instead. This substitution should be
# reconciled with the project's real utils/logger.py at review time — see
# DAY41_DECISIONS.md.
import logging
from typing import Dict, Tuple

from decision_ai.decision_models import (
    HiringFit,
    RoleLevel,
    RoundContribution,
    RoundScores,
    UnifiedScore,
    UnifiedScoreBreakdown,
)
from decision_ai.round_weights import get_weights

from utils.logger import get_logger
logger = get_logger(__name__)

_ROUND_FIELD_MAP: Dict[str, str] = {
    "ats": "ats_score",
    "screening": "screening_score",
    "hr": "hr_score",
}


def redistribute_weights(
    round_scores: RoundScores, base_weights: Dict[str, float]
) -> Dict[str, float]:
    """Drop weights for missing rounds and renormalize the remainder to 1.0.

    Args:
        round_scores: The candidate's raw round scores (some may be None).
        base_weights: The base (pre-redistribution) weights for all three
            rounds, keyed by "ats" / "screening" / "hr".

    Returns:
        A dict of weights for only the present rounds, renormalized so
        they sum to 1.0.

    Raises:
        ValueError: If all three round scores are None.
    """
    present_rounds = [
        name
        for name, field in _ROUND_FIELD_MAP.items()
        if getattr(round_scores, field) is not None
    ]

    if not present_rounds:
        raise ValueError(
            "No round scores provided — cannot compute unified score"
        )

    present_weight_sum = sum(base_weights[name] for name in present_rounds)

    redistributed = {
        name: base_weights[name] / present_weight_sum for name in present_rounds
    }
    return redistributed


def calculate_unified_score(
    round_scores: RoundScores, weights: Dict[str, float]
) -> Tuple[float, UnifiedScoreBreakdown]:
    """Compute the final weighted score from already-redistributed weights.

    Args:
        round_scores: The candidate's raw round scores.
        weights: Already-redistributed weights (sums to 1.0) for the
            present rounds only. This function does not call
            redistribute_weights() itself.

    Returns:
        A tuple of (final_score rounded to 2 decimal places,
        UnifiedScoreBreakdown).
    """
    contributions = []
    rounds_included = []
    rounds_missing = []

    for name, field in _ROUND_FIELD_MAP.items():
        raw_score = getattr(round_scores, field)
        if raw_score is None:
            rounds_missing.append(name)
            continue

        rounds_included.append(name)
        weight_used = weights[name]
        weighted_contribution = raw_score * weight_used
        contributions.append(
            RoundContribution(
                round_name=name,
                raw_score=raw_score,
                weight_used=weight_used,
                weighted_contribution=weighted_contribution,
            )
        )

    final_score = round(
        sum(c.weighted_contribution for c in contributions), 2
    )

    breakdown = UnifiedScoreBreakdown(
        contributions=contributions,
        rounds_included=rounds_included,
        rounds_missing=rounds_missing,
    )

    return final_score, breakdown


def calculate_hiring_fit(score: float) -> HiringFit:
    """Map a final score to a hiring-fit percentage and category.

    Args:
        score: The final unified score (0-100).

    Returns:
        A HiringFit model with the percentage (same as score) and category.
    """
    if score >= 80:
        category = "Excellent Fit"
    elif score >= 65:
        category = "Good Fit"
    elif score >= 50:
        category = "Moderate Fit"
    else:
        category = "Low Fit"

    return HiringFit(hiring_fit_percentage=score, fit_category=category)


def get_recommendation(score: float) -> str:
    """Map a final score to a lowercase recommendation string.

    Args:
        score: The final unified score (0-100).

    Returns:
        One of "selected", "hold", "rejected" (lowercase, exact values,
        matching the platform's Decision & Scoring Service I/O contract).
    """
    if score >= 75:
        return "selected"
    elif score >= 55:
        return "hold"
    else:
        return "rejected"


def get_confidence(round_scores: RoundScores) -> str:
    """Derive a confidence rating from how many rounds are present.

    Args:
        round_scores: The candidate's raw round scores.

    Returns:
        "high" if all 3 rounds are present, "medium" if 2 are present,
        "low" if 1 is present. This function is standalone and does not
        assume it is only ever called after redistribute_weights().
    """
    present_count = sum(
        1
        for field in _ROUND_FIELD_MAP.values()
        if getattr(round_scores, field) is not None
    )

    if present_count == 3:
        return "high"
    elif present_count == 2:
        return "medium"
    else:
        return "low"


def generate_reasoning(
    breakdown: UnifiedScoreBreakdown, recommendation: str
) -> str:
    """Build deterministic, data-derived reasoning text.

    Args:
        breakdown: The UnifiedScoreBreakdown produced by
            calculate_unified_score().
        recommendation: The recommendation string ("selected"/"hold"/
            "rejected").

    Returns:
        A human-readable reasoning string derived from the actual
        RoundContribution data. No LLM calls, no canned strings.
    """
    total_score = round(
        sum(c.weighted_contribution for c in breakdown.contributions), 2
    )

    if breakdown.contributions:
        top_contribution = max(
            breakdown.contributions, key=lambda c: c.weighted_contribution
        )
        others = [
            c.round_name
            for c in breakdown.contributions
            if c.round_name != top_contribution.round_name
        ]
        if others:
            others_text = " and ".join(others)
            included_sentence = (
                f"Final score driven primarily by {top_contribution.round_name} "
                f"(contributed {top_contribution.weighted_contribution:.2f} of "
                f"{total_score:.2f} total). {others_text} also included."
            )
        else:
            included_sentence = (
                f"Final score based solely on {top_contribution.round_name} "
                f"(contributed {top_contribution.weighted_contribution:.2f} of "
                f"{total_score:.2f} total)."
            )
    else:
        included_sentence = "No round contributions were available."

    if breakdown.rounds_missing:
        missing_text = ", ".join(breakdown.rounds_missing)
        missing_sentence = (
            f" {missing_text} "
            f"{'was' if len(breakdown.rounds_missing) == 1 else 'were'} "
            f"not completed and {'was' if len(breakdown.rounds_missing) == 1 else 'were'} "
            f"excluded; remaining round weights were proportionally redistributed."
        )
    else:
        missing_sentence = " All three rounds were included with no redistribution needed."

    recommendation_sentence = f" Recommendation: {recommendation}."

    return included_sentence + missing_sentence + recommendation_sentence


def unified_scoring_pipeline(
    candidate_id: str,
    round_scores: RoundScores,
    role_level: RoleLevel = RoleLevel.mid,
) -> UnifiedScore:
    """Single public entry point: run the full unified scoring pipeline.

    Orchestrates get_weights -> redistribute_weights ->
    calculate_unified_score -> calculate_hiring_fit -> get_recommendation
    -> get_confidence -> generate_reasoning -> assemble UnifiedScore.

    Args:
        candidate_id: Identifier of the candidate being scored.
        round_scores: The candidate's raw round scores.
        role_level: The role level used to select base weights. Defaults
            to RoleLevel.mid.

    Returns:
        A fully populated UnifiedScore model.

    Raises:
        ValueError: If all three round scores are None (propagated from
            redistribute_weights).
    """
    logger.info("Starting unified scoring pipeline for candidate=%s", candidate_id)

    base_weights = get_weights(role_level)
    redistributed_weights = redistribute_weights(round_scores, base_weights)
    final_score, breakdown = calculate_unified_score(
        round_scores, redistributed_weights
    )
    hiring_fit = calculate_hiring_fit(final_score)
    recommendation = get_recommendation(final_score)
    confidence = get_confidence(round_scores)
    reasoning = generate_reasoning(breakdown, recommendation)

    result = UnifiedScore(
        candidate_id=candidate_id,
        final_score=final_score,
        recommendation=recommendation,
        confidence=confidence,
        breakdown=breakdown,
        hiring_fit=hiring_fit,
        reasoning=reasoning,
        role_level_used=role_level,
    )

    logger.info(
        "Completed unified scoring pipeline for candidate=%s final_score=%s recommendation=%s",
        candidate_id,
        final_score,
        recommendation,
    )

    return result
