"""
interview_ai/hr_scoring_engine.py

Day 37 HR interview scoring engine. Combines caller-supplied relevance,
communication, and confidence sub-scores with a derived consistency
sub-score into a per-answer and per-interview HR score.

Part of the interview_ai module — fully isolated from screening_ai/,
ats_engine/, and scoring/. Only imports from interview_ai.hr_scoring_models,
interview_ai.hr_weights, and interview_ai.interview_models, which are
permitted intra-module imports.
"""

from interview_ai.hr_scoring_models import (
    HRAnswerScore,
    HRAnswerScoreBreakdown,
    HRInterviewScore,
)
from interview_ai.hr_weights import DEFAULT_WEIGHTS, get_weights
from interview_ai.interview_models import RoleLevel

from utils.logger import get_logger

logger = get_logger(__name__)


def score_consistency(contradiction_detected: bool, is_vague: bool) -> float:
    """Derive a consistency sub-score from behavioral flags.

    Args:
        contradiction_detected: True if a contradiction was flagged
            for this answer.
        is_vague: True if the answer was flagged as vague.

    Returns:
        0.3 if a contradiction was detected, 0.6 if the answer was
        vague (and no contradiction), or 1.0 if neither flag is set.
    """
    if contradiction_detected:
        return 0.3
    if is_vague:
        return 0.6
    return 1.0


def score_hr_answer(
    question_id: str,
    relevance_score: float,
    communication_score: float,
    confidence_score: float,
    contradiction_detected: bool = False,
    is_vague: bool = False,
    weights: dict[str, float] = DEFAULT_WEIGHTS,
) -> HRAnswerScore:
    """Compute the HR score for a single candidate answer.

    Args:
        question_id: Identifier of the question being scored.
        relevance_score: Caller-supplied relevance sub-score (0.0–1.0).
        communication_score: Caller-supplied communication sub-score (0.0–1.0).
        confidence_score: Caller-supplied confidence sub-score (0.0–1.0).
        contradiction_detected: True if a contradiction was flagged for this answer.
        is_vague: True if the answer was flagged as vague.
        weights: Dimension weights to apply, keyed by
            "relevance", "communication", "confidence", "consistency".

    Returns:
        An HRAnswerScore with the final 0–100 score and full breakdown.
    """
    consistency = score_consistency(contradiction_detected, is_vague)

    final = (
        relevance_score * weights["relevance"]
        + communication_score * weights["communication"]
        + confidence_score * weights["confidence"]
        + consistency * weights["consistency"]
    )
    final_score = round(final * 100, 2)

    breakdown = HRAnswerScoreBreakdown(
        relevance=relevance_score,
        communication=communication_score,
        confidence=confidence_score,
        consistency=consistency,
    )

    return HRAnswerScore(
        question_id=question_id,
        final_score=final_score,
        breakdown=breakdown,
    )


def aggregate_hr_scores(scored_answers: list[HRAnswerScore]) -> float:
    """Aggregate per-answer HR scores into a single interview score.

    Uses the arithmetic mean rather than a sum, so the aggregate score
    is length-normalized: a 3-question and a 6-question interview
    produce comparable aggregate scores.

    Args:
        scored_answers: List of per-answer HR scores.

    Returns:
        The mean of all final_score values, rounded to 2 d.p., or
        0.0 if the list is empty.
    """
    if not scored_answers:
        return 0.0
    mean_score = sum(answer.final_score for answer in scored_answers) / len(scored_answers)
    return round(mean_score, 2)


def get_hr_decision(score: float) -> str:
    """Map an aggregate HR score to a hiring decision label.

    Args:
        score: Aggregate HR interview score (0.0–100.0).

    Returns:
        "Strong Hire" if score >= 75, "Consider" if score >= 55,
        otherwise "Reject".
    """
    if score >= 75:
        return "Strong Hire"
    if score >= 55:
        return "Consider"
    return "Reject"


def hr_scoring_pipeline(
    answers: list[dict],
    role_level: RoleLevel = RoleLevel.fresher,
) -> HRInterviewScore:
    """Score a full HR interview from raw per-answer input dicts.

    Args:
        answers: List of dicts, each containing:
            question_id (str),
            relevance_score (float, 0.0–1.0),
            communication_score (float, 0.0–1.0),
            confidence_score (float, 0.0–1.0),
            contradiction_detected (bool, optional, default False),
            is_vague (bool, optional, default False).
        role_level: Candidate's resolved role level, used to select
            the scoring weights.

    Returns:
        An HRInterviewScore with the aggregate hr_score, decision,
        and all per-answer scored results.
    """
    weights = get_weights(role_level)

    scored_answers: list[HRAnswerScore] = []
    for answer in answers:
        scored_answers.append(
            score_hr_answer(
                question_id=answer.get("question_id"),
                relevance_score=answer.get("relevance_score"),
                communication_score=answer.get("communication_score"),
                confidence_score=answer.get("confidence_score"),
                contradiction_detected=answer.get("contradiction_detected", False),
                is_vague=answer.get("is_vague", False),
                weights=weights,
            )
        )

    hr_score = aggregate_hr_scores(scored_answers)
    decision = get_hr_decision(hr_score)

    logger.info("HR interview scored: hr_score=%s, decision=%s", hr_score, decision)

    return HRInterviewScore(
        hr_score=hr_score,
        decision=decision,
        scored_answers=scored_answers,
    )
