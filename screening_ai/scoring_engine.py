"""
screening_ai/scoring_engine.py

Screening scoring engine for the Zecpath AI pipeline.

Consumes answer dicts from screening_ai.answer_engine.process_answer() and
produces dimension scores, a weighted final score, and an overall screening
decision.  Sits between the Answer Engine (Day 25) and downstream reporting.
"""

from utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_WEIGHTS: dict[str, float] = {
    "clarity": 0.25,
    "relevance": 0.30,
    "completeness": 0.25,
    "consistency": 0.20,
}


# ---------------------------------------------------------------------------
# Dimension scorers
# ---------------------------------------------------------------------------


def score_clarity(answer: dict) -> float:
    """Score answer clarity based on word count of the original text.

    Thresholds:
        >12 words → 1.0
        >6  words → 0.7
        >2  words → 0.4
        else      → 0.0

    Args:
        answer: A dict as returned by answer_engine.process_answer().

    Returns:
        Clarity score in [0.0, 1.0].
    """
    logger.debug(
        "score_clarity called for question_id=%s", answer.get("question_id")
    )
    word_count = len(answer["original_text"].split())
    if word_count > 12:
        result = 1.0
    elif word_count > 6:
        result = 0.7
    elif word_count > 2:
        result = 0.4
    else:
        result = 0.0
    logger.debug("score_clarity → %.2f (word_count=%d)", result, word_count)
    return result


def score_relevance(answer: dict) -> float:
    """Score answer relevance based on the off-topic flag, with a keyword-match override.

    Day 25's classify_intent() uses literal keyword matching against generic HR
    categories (introduction, experience, skills, salary, availability, education,
    location). This means domain-specific technical answers — e.g. an answer full of
    QE terminology like FMEA, APQP, SPC, CAPA — are classified as intent="unknown"
    because they never contain literal words like "skills" or "tools". This makes
    off_topic=True for every technically accurate domain answer, regardless of quality.

    To correct for this without touching answer_engine.py's intent classification,
    relevance scoring treats a non-empty keywords_found list (matched against the
    Day 22 question bank's expected_keywords) as independent evidence the answer IS
    on-topic, even when off_topic=True. This means a literal keyword hit against the
    question's own expected vocabulary overrides a failed generic intent match.

    Scoring (first match wins):
        off_topic == False                                  → 1.0
        off_topic == True  AND keywords_found is non-empty   → 0.8
        off_topic == True  AND keywords_found is empty        → 0.3

    Args:
        answer: A dict as returned by answer_engine.process_answer().

    Returns:
        Relevance score in {0.3, 0.8, 1.0}.
    """
    logger.debug(
        "score_relevance called for question_id=%s", answer.get("question_id")
    )
    if not answer["off_topic"]:
        result = 1.0
    elif answer["keywords_found"]:
        result = 0.8
        logger.debug(
            "score_relevance keyword-match override applied for question_id=%s "
            "(off_topic=True but keywords_found=%s)",
            answer.get("question_id"),
            answer["keywords_found"],
        )
    else:
        result = 0.3
    logger.debug(
        "score_relevance → %.2f (off_topic=%s, keywords_found=%s)",
        result,
        answer["off_topic"],
        answer["keywords_found"],
    )
    return result


def score_completeness(answer: dict) -> float:
    """Score answer completeness using three additive signals, capped at 1.0.

    Scoring:
        +0.4 if keywords_found is non-empty
        +0.3 if experience_years > 0
        +0.3 if availability != "Unknown"

    Args:
        answer: A dict as returned by answer_engine.process_answer().

    Returns:
        Completeness score in [0.0, 1.0].
    """
    logger.debug(
        "score_completeness called for question_id=%s", answer.get("question_id")
    )
    score = 0.0
    if answer["keywords_found"]:
        score += 0.4
    if answer["experience_years"] > 0:
        score += 0.3
    if answer["availability"] != "Unknown":
        score += 0.3
    result = min(score, 1.0)
    logger.debug("score_completeness → %.2f", result)
    return result


def score_consistency(answer: dict) -> float:
    """Score answer consistency based on vagueness and off-topic signals, with a
    keyword-match override for the off-topic branch.

    Same root cause as score_relevance()'s keyword override: Day 25's classify_intent()
    cannot recognize domain-specific technical answers, so off_topic=True fires on every
    technically accurate QE answer regardless of quality. Without an override here, a
    confident domain-expert answer with zero vagueness is penalized to 0.2, while a vague,
    hedging answer that happens to be classified as not-off-topic scores higher. This
    inverted the expected ranking in the Day 30 simulation: a hesitant/uncertain candidate
    out-scored a confident/accurate one because consistency was the deciding dimension.

    Evaluation order (first match wins):
        is_vague == True                                      → 0.3
        off_topic == True AND keywords_found is non-empty      → 0.7
        off_topic == True AND keywords_found is empty           → 0.2
        else                                                   → 1.0

    is_vague is checked first regardless of keyword evidence — genuine hedging language
    is still a real consistency problem even in an answer that hits the right keywords.
    The keyword override only softens the off-topic-alone penalty, it does not erase the
    vagueness penalty.

    0.7 (not 1.0) is used for the override, mirroring the same reasoning as
    score_relevance()'s 0.8: a keyword hit is good evidence the answer is consistent with
    the question's subject matter, but it is not as strong as a clean intent match
    combined with no vagueness, so it does not fully equal a perfectly consistent answer.

    Args:
        answer: A dict as returned by answer_engine.process_answer().

    Returns:
        Consistency score in {0.2, 0.3, 0.7, 1.0}.
    """
    logger.debug(
        "score_consistency called for question_id=%s", answer.get("question_id")
    )
    if answer["is_vague"]:
        result = 0.3
    elif answer["off_topic"] and answer["keywords_found"]:
        result = 0.7
        logger.debug(
            "score_consistency keyword-match override applied for question_id=%s "
            "(off_topic=True but keywords_found=%s)",
            answer.get("question_id"),
            answer["keywords_found"],
        )
    elif answer["off_topic"]:
        result = 0.2
    else:
        result = 1.0
    logger.debug(
        "score_consistency → %.2f (is_vague=%s, off_topic=%s, keywords_found=%s)",
        result,
        answer["is_vague"],
        answer["off_topic"],
        answer["keywords_found"],
    )
    return result


# ---------------------------------------------------------------------------
# Composite scorer
# ---------------------------------------------------------------------------


def score_answer(answer: dict, weights: dict | None = None) -> dict:
    """Score a single answer across all four dimensions and compute a final score.

    Args:
        answer: A dict as returned by answer_engine.process_answer().
        weights: Optional dimension weight overrides.  Falls back to
            DEFAULT_WEIGHTS when ``None``.

    Returns:
        A dict with keys:
            question_id  — echoed from the input answer
            scores       — per-dimension scores, each rounded to 2 d.p.
            final_score  — weighted sum expressed as a percentage (0–100),
                           rounded to 2 d.p.
            weights_used — the weight dict that was applied
    """
    logger.debug(
        "score_answer called for question_id=%s", answer.get("question_id")
    )
    weights = weights if weights is not None else DEFAULT_WEIGHTS

    clarity = score_clarity(answer)
    relevance = score_relevance(answer)
    completeness = score_completeness(answer)
    consistency = score_consistency(answer)

    final = (
        clarity * weights["clarity"]
        + relevance * weights["relevance"]
        + completeness * weights["completeness"]
        + consistency * weights["consistency"]
    )

    result = {
        "question_id": answer["question_id"],
        "scores": {
            "clarity": round(clarity, 2),
            "relevance": round(relevance, 2),
            "completeness": round(completeness, 2),
            "consistency": round(consistency, 2),
        },
        "final_score": round(final * 100, 2),
        "weights_used": weights,
    }
    logger.debug(
        "score_answer exit — final_score=%.2f for question_id=%s",
        result["final_score"],
        answer.get("question_id"),
    )
    return result


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def aggregate_screening_score(
    scored_answers: list[dict],
    importance_weights: list[int] | None = None,
) -> dict:
    """Aggregate per-question scores into an overall screening result.

    Uses a weighted average when *importance_weights* is provided and its
    length matches *scored_answers*; otherwise falls back to a simple mean.

    Decision thresholds (applied to the 0–100 final score):
        >= 70 → "Pass"
        >= 50 → "Review"
        else  → "Reject"

    Args:
        scored_answers: List of dicts as returned by score_answer().
        importance_weights: Optional integer importance values, one per
            answer.  Mismatched length silently triggers the simple average.

    Returns:
        A dict with keys:
            screening_score  — overall score (0–100), rounded to 2 d.p.
            decision         — "Pass" | "Review" | "Reject"
            total_questions  — number of answers scored
            breakdown        — the full list of scored_answers
    """
    logger.debug(
        "aggregate_screening_score called with %d scored answer(s)",
        len(scored_answers),
    )
    raw_scores = [sa["final_score"] for sa in scored_answers]

    use_weighted = (
        importance_weights is not None
        and len(importance_weights) == len(scored_answers)
    )

    if use_weighted:
        total_importance = sum(importance_weights)  # type: ignore[arg-type]
        if total_importance == 0:
            final = sum(raw_scores) / len(raw_scores) if raw_scores else 0.0
        else:
            final = (
                sum(s * w for s, w in zip(raw_scores, importance_weights))  # type: ignore[arg-type]
                / total_importance
            )
        logger.debug("aggregate_screening_score using importance-weighted average")
    else:
        final = sum(raw_scores) / len(raw_scores) if raw_scores else 0.0
        logger.debug("aggregate_screening_score using simple average")

    if final >= 70:
        decision = "Pass"
    elif final >= 50:
        decision = "Review"
    else:
        decision = "Reject"

    result = {
        "screening_score": round(final, 2),
        "decision": decision,
        "total_questions": len(scored_answers),
        "breakdown": scored_answers,
    }
    logger.debug(
        "aggregate_screening_score exit — screening_score=%.2f, decision=%s",
        result["screening_score"],
        decision,
    )
    return result


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


def screening_scoring_pipeline(
    answers: list[dict],
    weights: dict | None = None,
    importance_weights: list[int] | None = None,
) -> dict:
    """Run the full scoring pipeline: score each answer then aggregate.

    Args:
        answers: List of answer dicts as returned by
            answer_engine.process_answer() or process_answers_batch().
        weights: Optional dimension weight overrides passed to score_answer().
        importance_weights: Optional per-question importance weights passed
            to aggregate_screening_score().

    Returns:
        The aggregate screening result dict from aggregate_screening_score().
    """
    logger.debug(
        "screening_scoring_pipeline called with %d answer(s)", len(answers)
    )
    try:
        scored = [score_answer(answer, weights) for answer in answers]
        result = aggregate_screening_score(scored, importance_weights)
    except Exception as e:
        logger.error("screening_scoring_pipeline failed: %s", e)
        raise
    logger.debug(
        "screening_scoring_pipeline complete — decision=%s", result["decision"]
    )
    return result
