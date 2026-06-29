"""Tests for the screening report generator.

All answer, score, and behavior dicts are constructed manually to match
the exact output schemas of the Day 25 answer engine, Day 26 scoring
engine, and Day 27 behavior report engine. No mocking is used, and no
imports from those modules are needed.
"""

from screening_ai.report_generator import generate_screening_report


def _make_answer(
    question_id: str = "q1",
    original_text: str = "I have relevant experience for this role.",
    keywords_found: list | None = None,
    salary: str | None = None,
    availability: str = "Unknown",
    is_vague: bool = False,
    off_topic: bool = False,
) -> dict:
    """Build an answer dict matching the Day 25 answer_engine output schema.

    Args:
        question_id: Identifier of the question this answer responds to.
        original_text: The candidate's raw answer text.
        keywords_found: Skill keywords detected in the answer. Defaults
            to an empty list when not provided.
        salary: The candidate's stated salary expectation, or None.
        availability: The candidate's stated availability, defaulting
            to ``"Unknown"`` when not stated.
        is_vague: Whether the answer was flagged as vague.
        off_topic: Whether the answer was flagged as off-topic.

    Returns:
        A dict matching the process_answer() output schema.
    """
    return {
        "question_id": question_id,
        "original_text": original_text,
        "intent": "general",
        "keywords_found": keywords_found if keywords_found is not None else [],
        "experience_years": 0,
        "salary": salary,
        "availability": availability,
        "is_vague": is_vague,
        "off_topic": off_topic,
        "missing_answer": False,
    }


def _make_score(question_id: str = "q1", final_score: float = 70.0) -> dict:
    """Build a score dict matching the Day 26 scoring_engine output schema.

    Args:
        question_id: Identifier of the question this score corresponds to.
        final_score: The final numeric score assigned to the answer.

    Returns:
        A dict matching the score_answer() output schema.
    """
    return {
        "question_id": question_id,
        "scores": {"relevance": final_score / 100},
        "final_score": final_score,
        "weights_used": {"relevance": 1.0},
    }


def _make_behavior(communication_strength: str = "Moderate") -> dict:
    """Build a behavior dict matching the Day 27 behavior_report output schema.

    Args:
        communication_strength: The overall communication strength label.

    Returns:
        A dict matching the generate_behavior_report() output schema.
    """
    return {
        "confidence": {"confidence_score": 0.7, "signals": {}},
        "sentiment": {"sentiment": "Neutral", "sentiment_score": 0.5},
        "behavior_flags": {"uncertainty": False, "contradiction": False},
        "communication_strength": communication_strength,
    }


def test_report_structure() -> None:
    """generate_screening_report should return all expected top-level keys."""
    report = generate_screening_report(
        "cand-1", "job-1", [_make_answer()], [_make_score()], [_make_behavior()]
    )

    assert set(report.keys()) == {
        "candidate_id",
        "job_id",
        "final_score",
        "decision",
        "summary",
        "highlights",
        "answers",
    }


def test_decision_proceed() -> None:
    """A final_score of 70 or above should yield decision='Proceed'."""
    report = generate_screening_report(
        "cand-1",
        "job-1",
        [_make_answer()],
        [_make_score(final_score=80.0)],
        [_make_behavior()],
    )

    assert report["decision"] == "Proceed"


def test_decision_review() -> None:
    """A final_score between 50 and 69 should yield decision='Review'."""
    report = generate_screening_report(
        "cand-1",
        "job-1",
        [_make_answer()],
        [_make_score(final_score=60.0)],
        [_make_behavior()],
    )

    assert report["decision"] == "Review"


def test_decision_reject() -> None:
    """A final_score below 50 should yield decision='Reject'."""
    report = generate_screening_report(
        "cand-1",
        "job-1",
        [_make_answer()],
        [_make_score(final_score=30.0)],
        [_make_behavior()],
    )

    assert report["decision"] == "Reject"


def test_strength_detected() -> None:
    """A final_score of 85 should produce a non-empty strengths list."""
    report = generate_screening_report(
        "cand-1",
        "job-1",
        [_make_answer(question_id="q1")],
        [_make_score(question_id="q1", final_score=85.0)],
        [_make_behavior()],
    )

    assert len(report["summary"]["strengths"]) > 0


def test_risk_detected() -> None:
    """communication_strength='Weak' should produce a non-empty risks list."""
    report = generate_screening_report(
        "cand-1",
        "job-1",
        [_make_answer()],
        [_make_score(final_score=90.0)],
        [_make_behavior(communication_strength="Weak")],
    )

    assert len(report["summary"]["risks"]) > 0


def test_highlights_extracted() -> None:
    """Salary and availability from the answer should surface in highlights."""
    report = generate_screening_report(
        "cand-1",
        "job-1",
        [_make_answer(salary="8 lpa", availability="Immediate")],
        [_make_score()],
        [_make_behavior()],
    )

    assert report["highlights"]["salary_expectation"] == "8 lpa"
    assert report["highlights"]["availability"] == "Immediate"


def test_confirmed_skills() -> None:
    """Keywords found in the answer should surface in confirmed_skills."""
    report = generate_screening_report(
        "cand-1",
        "job-1",
        [_make_answer(keywords_found=["FMEA", "SPC"])],
        [_make_score()],
        [_make_behavior()],
    )

    assert "FMEA" in report["highlights"]["confirmed_skills"]
    assert "SPC" in report["highlights"]["confirmed_skills"]
