"""
technical_ai/technical_scoring_engine.py

Day 47 technical interview answer scoring engine. Combines a
caller-supplied accuracy sub-score with three text-derived sub-scores
(depth, logic, real_world) into a per-answer and per-interview
technical score.

IMPORTANT: this engine does NOT classify answer correctness. `accuracy`
is always a caller-supplied float in [0.0, 1.0], mirroring the
caller-supplied relevance_score pattern in interview_ai's
hr_scoring_engine.py. This is the technical-track counterpart of the
same open platform backlog item covering live answer-quality
classification -- do not attempt to infer correctness from answer text
in this file. See technical_ai/DAY47_DECISIONS.md, item 1.

Part of the technical_ai module -- fully isolated from interview_ai/,
screening_ai/, ats_engine/, and scoring/. Only imports from
technical_ai.technical_scoring_models (intra-module, permitted). The
marker constants below are duplicated by value from the pattern used
in interview_ai/aptitude_scoring.py, not imported from it -- module
isolation applies to constants as well as logic. See
technical_ai/DAY47_DECISIONS.md, item 4.

DETERMINISM RULE (non-negotiable, project-wide): no use of the
`random` module anywhere in this file.
"""

import re

from utils.logger import get_logger

from technical_ai.technical_scoring_models import (
    TechnicalAnswerScore,
    TechnicalAnswerScoreBreakdown,
    TechnicalInterviewScore,
)

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Marker constants
# ---------------------------------------------------------------------------

# Defined independently from interview_ai.aptitude_scoring's marker lists
# despite the shared ratio-based scoring technique -- these are
# QE-technical-domain specific, not generic reasoning markers, and are
# duplicated by value, never by import, per project convention.
DEPTH_MARKERS: list[str] = [
    "root cause",
    "because",
    "impact",
    "risk",
    "tolerance",
    "specification",
    "deviation",
    "trade-off",
]

LOGIC_MARKERS: list[str] = [
    "first",
    "then",
    "therefore",
    "as a result",
    "which means",
    "so that",
    "because of this",
]

REAL_WORLD_MARKERS: list[str] = [
    "in practice",
    "on the production line",
    "for example",
    "in our facility",
    "during an audit",
    "real-world",
    "in the field",
]

# ---------------------------------------------------------------------------
# Weights
# ---------------------------------------------------------------------------

DEFAULT_WEIGHTS: dict[str, float] = {
    "accuracy": 0.40,
    "depth": 0.30,
    "logic": 0.20,
    "real_world": 0.10,
}
assert sum(DEFAULT_WEIGHTS.values()) == 1.0

# ---------------------------------------------------------------------------
# Phase scoping
# ---------------------------------------------------------------------------

# Plain strings matching TechnicalInterviewPhase values, not the enum
# itself, to keep this file's phase-filtering logic decoupled from
# importing the enum type directly in this constant.
#
# introduction and closing phase questions are logistics/rapport-oriented
# and are deliberately excluded from technical depth scoring, mirroring
# how the HR interview engine's communication scoring is phase-agnostic
# but this technical engine is phase-scoped. See DAY47_DECISIONS.md,
# item 3.
SCORABLE_PHASES: frozenset[str] = frozenset(
    {"experience_based", "conceptual", "scenario_based"}
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _distinct_marker_count(text: str, markers: list[str]) -> int:
    """
    Count how many distinct markers from `markers` appear in `text` at
    least once, using word-boundary regex matching (not raw occurrence
    counts).

    Identical in behavior to interview_ai.aptitude_scoring's private
    helper of the same name (duplicated by value, not imported).

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


def score_depth(text: str) -> float:
    """Score depth of explanation using distinct DEPTH_MARKERS detection.

    Ratio of distinct markers found to a denominator capped at 4. No
    length floor is applied.

    Args:
        text: Cleaned candidate answer text.

    Returns:
        A float in [0.0, 1.0] rounded to 4 decimal places.
    """
    logger.debug("score_depth called with text=%r", text)
    distinct_found = _distinct_marker_count(text, DEPTH_MARKERS)
    denominator = min(len(DEPTH_MARKERS), 4)
    ratio = distinct_found / denominator
    result = round(min(max(ratio, 0.0), 1.0), 4)
    logger.debug(
        "score_depth → %.4f (distinct_found=%d, denominator=%d)",
        result,
        distinct_found,
        denominator,
    )
    return result


def score_logic(text: str) -> float:
    """Score logical reasoning structure using distinct LOGIC_MARKERS detection.

    Ratio of distinct markers found to a denominator capped at 4. No
    length floor is applied.

    Args:
        text: Cleaned candidate answer text.

    Returns:
        A float in [0.0, 1.0] rounded to 4 decimal places.
    """
    logger.debug("score_logic called with text=%r", text)
    distinct_found = _distinct_marker_count(text, LOGIC_MARKERS)
    denominator = min(len(LOGIC_MARKERS), 4)
    ratio = distinct_found / denominator
    result = round(min(max(ratio, 0.0), 1.0), 4)
    logger.debug(
        "score_logic → %.4f (distinct_found=%d, denominator=%d)",
        result,
        distinct_found,
        denominator,
    )
    return result


def score_real_world(text: str) -> float:
    """Score real-world applicability using distinct REAL_WORLD_MARKERS detection.

    Ratio of distinct markers found to a denominator capped at 3. A
    length floor is applied: if word_count < 6, the result is capped at
    0.5 regardless of marker matches -- same floor rationale as
    interview_ai.aptitude_scoring.score_problem_solving, so a short
    answer containing "for example" should not score 1.0.

    Args:
        text: Cleaned candidate answer text.

    Returns:
        A float in [0.0, 1.0] rounded to 4 decimal places.
    """
    logger.debug("score_real_world called with text=%r", text)
    distinct_found = _distinct_marker_count(text, REAL_WORLD_MARKERS)
    denominator = min(len(REAL_WORLD_MARKERS), 3)
    ratio = distinct_found / denominator
    result = min(max(ratio, 0.0), 1.0)

    word_count = len(text.split())
    if word_count < 6:
        result = min(result, 0.5)
        logger.debug(
            "score_real_world: length floor applied (word_count=%d < 6).",
            word_count,
        )

    result = round(result, 4)
    logger.debug(
        "score_real_world → %.4f (distinct_found=%d, denominator=%d, word_count=%d)",
        result,
        distinct_found,
        denominator,
        word_count,
    )
    return result


def score_technical_answer(
    question_id: str,
    skill_domain: str,
    accuracy: float,
    text: str,
    weights: dict[str, float] = DEFAULT_WEIGHTS,
) -> TechnicalAnswerScore:
    """Score a single technical answer.

    Empty/whitespace-only `text` returns a zero-breakdown score
    (depth=logic=real_world=0.0) WITHOUT invoking the sub-scorers, the
    same empty-input pattern as
    interview_ai.aptitude_scoring.calculate_aptitude_score -- but
    `accuracy` is still applied as given, since it is caller-supplied
    and not derived from text. An empty answer would typically carry a
    caller-asserted accuracy of 0.0, but this function does not enforce
    that relationship; a WARNING is logged if text is empty AND
    accuracy > 0, since that combination is suspicious but not invalid.

    final_score = round(
        (accuracy * weights['accuracy'] + depth * weights['depth'] +
         logic * weights['logic'] + real_world * weights['real_world'])
        * 100,
        2,
    )

    Args:
        question_id: Identifier of the question being scored.
        skill_domain: TechnicalSkillDomain value this question belongs
            to, as a plain string.
        accuracy: Caller-supplied correctness sub-score (0.0-1.0).
        text: Cleaned candidate answer text. May be None, empty, or
            whitespace-only.
        weights: Dimension weights to apply, keyed by "accuracy",
            "depth", "logic", "real_world".

    Returns:
        A fully populated TechnicalAnswerScore Pydantic model instance.
    """
    logger.debug(
        "score_technical_answer called with question_id=%r, "
        "skill_domain=%r, accuracy=%r, text=%r",
        question_id,
        skill_domain,
        accuracy,
        text,
    )

    if not text or not text.strip():
        if accuracy > 0:
            logger.warning(
                "score_technical_answer received empty/whitespace-only "
                "text with accuracy=%.4f > 0 for question_id=%r; this "
                "combination is suspicious but not invalid.",
                accuracy,
                question_id,
            )
        depth = 0.0
        logic = 0.0
        real_world = 0.0
    else:
        depth = score_depth(text)
        logic = score_logic(text)
        real_world = score_real_world(text)

    final = (
        accuracy * weights["accuracy"]
        + depth * weights["depth"]
        + logic * weights["logic"]
        + real_world * weights["real_world"]
    )
    final_score = round(final * 100, 2)

    breakdown = TechnicalAnswerScoreBreakdown(
        accuracy=accuracy,
        depth=depth,
        logic=logic,
        real_world=real_world,
    )

    return TechnicalAnswerScore(
        question_id=question_id,
        skill_domain=skill_domain,
        final_score=final_score,
        breakdown=breakdown,
    )


def aggregate_technical_scores(scored_answers: list[TechnicalAnswerScore]) -> float:
    """Aggregate per-answer technical scores into a single interview score.

    Uses the arithmetic mean rather than a sum, so the aggregate score
    is length-normalized -- same rationale as
    interview_ai.hr_scoring_engine.aggregate_hr_scores.

    Args:
        scored_answers: List of per-answer technical scores.

    Returns:
        The mean of all final_score values, rounded to 2 d.p., or 0.0
        if the list is empty.
    """
    if not scored_answers:
        return 0.0
    mean_score = sum(answer.final_score for answer in scored_answers) / len(
        scored_answers
    )
    return round(mean_score, 2)


def get_skill_breakdown(
    scored_answers: list[TechnicalAnswerScore],
) -> dict[str, float]:
    """Group scored_answers by skill_domain and compute the mean
    final_score per domain.

    A domain with zero scored answers is simply absent from the
    returned dict -- absence is more honest than a fabricated zero,
    consistent with project-wide no-fabrication precedent. See
    technical_ai/DAY47_DECISIONS.md, item 5.

    Args:
        scored_answers: List of per-answer technical scores.

    Returns:
        A dict mapping skill_domain value to its mean final_score,
        rounded to 2 d.p.
    """
    totals: dict[str, float] = {}
    counts: dict[str, int] = {}

    for answer in scored_answers:
        totals[answer.skill_domain] = totals.get(answer.skill_domain, 0.0) + answer.final_score
        counts[answer.skill_domain] = counts.get(answer.skill_domain, 0) + 1

    return {
        domain: round(totals[domain] / counts[domain], 2) for domain in totals
    }


def get_technical_decision(score: float) -> str:
    """Map an aggregate technical score to a hiring-signal label.

    Args:
        score: Aggregate technical interview score (0.0-100.0).

    Returns:
        "Strong Technical Fit" if score >= 75, "Moderate Technical Fit"
        if score >= 55, otherwise "Weak Technical Fit".
    """
    if score >= 75:
        return "Strong Technical Fit"
    if score >= 55:
        return "Moderate Technical Fit"
    return "Weak Technical Fit"


def technical_scoring_pipeline(
    answers: list[dict],
    weights: dict[str, float] = DEFAULT_WEIGHTS,
) -> TechnicalInterviewScore:
    """Score a full technical interview from raw per-answer input dicts.

    Each dict must contain: question_id (str), skill_domain (str),
    phase (str), accuracy (float 0.0-1.0), text (str).

    DAY 42 FIX PRECEDENT (mirrored from
    interview_ai.hr_scoring_engine.hr_scoring_pipeline): required keys
    are explicitly validated as present and non-None BEFORE calling
    score_technical_answer, so a missing key surfaces as a clear,
    diagnosable ValueError naming exactly which field(s) are missing,
    rather than a raw TypeError deep inside a helper function. `text`
    may be an empty string -- that is valid input, not a missing key;
    only None triggers the ValueError.

    PHASE FILTERING: any answer dict whose 'phase' value is not in
    SCORABLE_PHASES is EXCLUDED from scoring -- an INFO line is logged
    naming the question_id and phase, and the answer is not included in
    scored_answers. This is not an error condition, just expected
    filtering (e.g. an introduction-phase answer dict passed in
    alongside conceptual/scenario answers is simply skipped, not
    rejected).

    If, after filtering, zero answers remain scorable, this returns a
    TechnicalInterviewScore with technical_score=0.0, decision="Weak
    Technical Fit", empty scored_answers, and empty skill_breakdown --
    no exception is raised for this case, since an interview consisting
    only of introduction/closing questions is a valid, if unusual,
    state.

    Args:
        answers: List of raw per-answer input dicts.
        weights: Dimension weights to apply to each scored answer.

    Returns:
        A TechnicalInterviewScore with the aggregate technical_score,
        decision, per-answer scored results, and skill_breakdown.
    """
    _REQUIRED_ANSWER_KEYS = (
        "question_id",
        "skill_domain",
        "phase",
        "accuracy",
        "text",
    )

    scorable_answers: list[dict] = []
    for answer in answers:
        phase = answer.get("phase")
        if phase not in SCORABLE_PHASES:
            logger.info(
                "technical_scoring_pipeline: excluding question_id=%r "
                "with non-scorable phase=%r.",
                answer.get("question_id"),
                phase,
            )
            continue
        scorable_answers.append(answer)

    if not scorable_answers:
        logger.info(
            "technical_scoring_pipeline: no scorable answers after phase "
            "filtering; returning zero-state result."
        )
        return TechnicalInterviewScore(
            technical_score=0.0,
            decision="Weak Technical Fit",
            scored_answers=[],
            skill_breakdown={},
        )

    scored_answers: list[TechnicalAnswerScore] = []
    for answer in scorable_answers:
        missing = [k for k in _REQUIRED_ANSWER_KEYS if answer.get(k) is None]
        if missing:
            raise ValueError(
                f"technical_scoring_pipeline received an answer dict "
                f"missing required field(s) {missing}: {answer!r}. "
                f"question_id, skill_domain, phase, accuracy, and text "
                f"must all be present and non-None (text may be an "
                f"empty string)."
            )
        scored_answers.append(
            score_technical_answer(
                question_id=answer["question_id"],
                skill_domain=answer["skill_domain"],
                accuracy=answer["accuracy"],
                text=answer["text"],
                weights=weights,
            )
        )

    technical_score = aggregate_technical_scores(scored_answers)
    skill_breakdown = get_skill_breakdown(scored_answers)
    decision = get_technical_decision(technical_score)

    logger.info(
        "Technical interview scored: technical_score=%s, decision=%s",
        technical_score,
        decision,
    )

    return TechnicalInterviewScore(
        technical_score=technical_score,
        decision=decision,
        scored_answers=scored_answers,
        skill_breakdown=skill_breakdown,
    )
