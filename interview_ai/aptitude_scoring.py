"""
interview_ai/aptitude_scoring.py

Aptitude evaluation engine for the Zecpath interview_ai module.

Receives already-cleaned candidate answer text and returns a 0-100
aptitude quality score covering reasoning structure, problem-solving
orientation, and decision-quality language. Ratio-based graduated
scoring throughout — no fixed 0.4/0.7/1.0 buckets triggered by a single
keyword hit (see DAY38_DECISIONS.md for rationale).

Fully isolated: does not import from screening_ai/, ats_engine/, or
scoring/. No I/O beyond the intra-module scenario_evaluator import, no
Redis, no random module usage — pure deterministic computation.

NOT wired into hr_scoring_engine.py — aptitude/HR score aggregation is
an explicit future Decision Service concern, out of scope for Day 38.
"""

import re

from utils.logger import get_logger

from interview_ai.aptitude_models import AptitudeScore, AptitudeScoreBreakdown
from interview_ai.scenario_evaluator import evaluate_scenario

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Defined independently from communication_engine.STRUCTURE_KEYWORDS despite
# conceptual overlap — interview_ai submodules duplicate shared word lists
# by value, never by import, per project convention.
REASONING_MARKERS: list[str] = [
    "first",
    "then",
    "next",
    "because",
    "therefore",
    "as a result",
    "which means",
    "so that",
]

PROBLEM_SOLVING_MARKERS: list[str] = [
    "approach",
    "solution",
    "solve",
    "steps",
    "plan",
    "method",
]

DECISION_MARKERS: list[str] = [
    "consider",
    "analyze",
    "evaluate",
    "prioritize",
    "weigh",
    "decide",
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _distinct_marker_count(text: str, markers: list[str]) -> int:
    """
    Count how many distinct markers from `markers` appear in `text` at
    least once, using word-boundary regex matching (not raw occurrence
    counts).

    Args:
        text: Cleaned candidate answer text.
        markers: List of marker phrases/words to search for.

    Returns:
        The number of distinct markers found at least once in the text.
    """
    text_lower = text.lower()
    found = 0
    for marker in markers:
        pattern = r"\b" + re.escape(marker) + r"\b"
        if re.search(pattern, text_lower):
            found += 1
    return found


# ---------------------------------------------------------------------------
# Public scoring functions
# ---------------------------------------------------------------------------


def score_structure(text: str) -> float:
    """Score reasoning structure using distinct REASONING_MARKERS detection.

    Counts the number of distinct REASONING_MARKERS present in the text
    (word-boundary regex, not raw occurrence count) and expresses it as a
    ratio against a denominator capped at 4, so a single well-structured
    answer can reach 1.0 without needing all 8 markers.

    Args:
        text: Cleaned candidate answer text.

    Returns:
        A float in [0.0, 1.0] rounded to 4 decimal places.
    """
    logger.debug("score_structure called with text=%r", text)
    distinct_found = _distinct_marker_count(text, REASONING_MARKERS)
    denominator = min(len(REASONING_MARKERS), 4)
    ratio = distinct_found / denominator
    result = round(min(max(ratio, 0.0), 1.0), 4)
    logger.debug(
        "score_structure → %.4f (distinct_found=%d, denominator=%d)",
        result,
        distinct_found,
        denominator,
    )
    return result


def score_problem_solving(text: str) -> float:
    """Score problem-solving orientation using distinct PROBLEM_SOLVING_MARKERS detection.

    Same ratio pattern as score_structure, with denominator capped at 3.
    A length floor is applied: if word_count < 6, the result is capped at
    0.5 regardless of marker matches, preventing a 2-word answer
    containing "plan" from scoring 1.0.

    Args:
        text: Cleaned candidate answer text.

    Returns:
        A float in [0.0, 1.0] rounded to 4 decimal places.
    """
    logger.debug("score_problem_solving called with text=%r", text)
    distinct_found = _distinct_marker_count(text, PROBLEM_SOLVING_MARKERS)
    denominator = min(len(PROBLEM_SOLVING_MARKERS), 3)
    ratio = distinct_found / denominator
    result = min(max(ratio, 0.0), 1.0)

    word_count = len(text.split())
    if word_count < 6:
        result = min(result, 0.5)
        logger.debug(
            "score_problem_solving: length floor applied (word_count=%d < 6).",
            word_count,
        )

    result = round(result, 4)
    logger.debug(
        "score_problem_solving → %.4f (distinct_found=%d, denominator=%d, word_count=%d)",
        result,
        distinct_found,
        denominator,
        word_count,
    )
    return result


def score_decision_quality(text: str) -> float:
    """Score decision-quality language using distinct DECISION_MARKERS detection.

    Same ratio pattern as score_structure, with denominator capped at 3.

    Args:
        text: Cleaned candidate answer text.

    Returns:
        A float in [0.0, 1.0] rounded to 4 decimal places.
    """
    logger.debug("score_decision_quality called with text=%r", text)
    distinct_found = _distinct_marker_count(text, DECISION_MARKERS)
    denominator = min(len(DECISION_MARKERS), 3)
    ratio = distinct_found / denominator
    result = round(min(max(ratio, 0.0), 1.0), 4)
    logger.debug(
        "score_decision_quality → %.4f (distinct_found=%d, denominator=%d)",
        result,
        distinct_found,
        denominator,
    )
    return result


def get_aptitude_level(score: float) -> str:
    """Map a numeric aptitude score to a qualitative level label.

    Defined independently of communication_engine.get_communication_level
    (duplicated by value, not imported) but reuses the same band names
    and cutoffs for consistency across interview_ai scoring engines.

    Args:
        score: Aptitude score in the range [0.0, 100.0].

    Returns:
        One of "Excellent" (>=85), "Good" (>=70), "Average" (>=50), or "Poor".
    """
    if score >= 85:
        return "Excellent"
    if score >= 70:
        return "Good"
    if score >= 50:
        return "Average"
    return "Poor"


def calculate_aptitude_score(
    text: str,
    scenario_type: str | None = None,
    scenario_answer: str | None = None,
) -> AptitudeScore:
    """Run the full aptitude evaluation pipeline on a cleaned answer string.

    Pipeline (applied only to non-empty input):
        1. score_structure         — distinct REASONING_MARKERS ratio
        2. score_problem_solving   — distinct PROBLEM_SOLVING_MARKERS ratio
                                      with a short-answer length floor
        3. score_decision_quality  — distinct DECISION_MARKERS ratio

    Weighted average:
        weighted = structure * 0.35 + problem_solving * 0.35
                   + decision_quality * 0.30

    If scenario_type is provided, evaluate_scenario is invoked against
    `scenario_answer` (falling back to `text` when scenario_answer is not
    separately supplied) and the result is blended into the final score:
        final = weighted * 0.7 + scenario_evaluation.match_ratio * 0.3
    Otherwise:
        final = weighted

    aptitude_score = round(final * 100, 2)

    Returns a zero AptitudeScore (all breakdown fields 0.0, no scenario
    evaluation) without invoking any sub-scorers when input is None,
    empty, or whitespace-only — matching communication_engine's
    empty-input pattern exactly.

    Args:
        text: Cleaned candidate answer text. May be None, empty, or
            whitespace-only.
        scenario_type: Optional scenario pattern key (e.g.
            "deadline_pressure") to blend a ScenarioEvaluation into the
            final score.
        scenario_answer: Optional separate text to evaluate against the
            scenario pattern. When omitted, `text` is used for scenario
            matching as well.

    Returns:
        A fully populated AptitudeScore Pydantic model instance.
    """
    logger.debug(
        "calculate_aptitude_score called with text=%r, scenario_type=%r",
        text,
        scenario_type,
    )

    if not text or not text.strip():
        logger.warning(
            "calculate_aptitude_score received empty or whitespace-only text; "
            "returning zero score without invoking sub-scorers."
        )
        return AptitudeScore(
            aptitude_score=0.0,
            breakdown=AptitudeScoreBreakdown(
                structure=0.0,
                problem_solving=0.0,
                decision_quality=0.0,
            ),
            scenario_evaluation=None,
            word_count=0,
        )

    word_count: int = len(text.split())
    structure: float = score_structure(text)
    problem_solving: float = score_problem_solving(text)
    decision_quality: float = score_decision_quality(text)

    weighted: float = (
        structure * 0.35 + problem_solving * 0.35 + decision_quality * 0.30
    )

    scenario_evaluation = None
    if scenario_type:
        eval_text = scenario_answer if scenario_answer else text
        scenario_evaluation = evaluate_scenario(eval_text, scenario_type)
        final = weighted * 0.7 + scenario_evaluation.match_ratio * 0.3
    else:
        final = weighted

    aptitude_score: float = round(final * 100, 2)

    logger.info(
        "calculate_aptitude_score → score=%.2f, word_count=%d, scenario_type=%r",
        aptitude_score,
        word_count,
        scenario_type,
    )

    return AptitudeScore(
        aptitude_score=aptitude_score,
        breakdown=AptitudeScoreBreakdown(
            structure=structure,
            problem_solving=problem_solving,
            decision_quality=decision_quality,
        ),
        scenario_evaluation=scenario_evaluation,
        word_count=word_count,
    )
