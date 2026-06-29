"""
tests/test_scoring_engine.py

8 pytest tests for the Day 26 Screening Scoring Engine.

Answer dicts are constructed manually to match the process_answer() output
schema — no mocking required.
"""

import pytest

from screening_ai.scoring_engine import (
    score_clarity,
    score_relevance,
    score_completeness,
    score_consistency,
    score_answer,
    screening_scoring_pipeline,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _answer(
    *,
    question_id: str = "q1",
    original_text: str = "I have three years of experience working with Python.",
    intent: str = "experience",
    keywords_found: list[str] | None = None,
    experience_years: int = 3,
    salary: str | None = None,
    availability: str = "Immediate",
    is_vague: bool = False,
    off_topic: bool = False,
    missing_answer: bool = False,
) -> dict:
    """Build a minimal answer dict matching the process_answer() output schema.

    keywords_found defaults to an empty list (not a hardcoded match like
    ["python"]) so that tests which don't explicitly set keywords_found don't
    silently trigger score_relevance()'s keyword-match override. Tests that
    need a keyword hit (e.g. test_completeness_full, test_relevance_keyword_override)
    pass keywords_found explicitly.
    """
    return {
        "question_id": question_id,
        "original_text": original_text,
        "intent": intent,
        "keywords_found": keywords_found if keywords_found is not None else [],
        "experience_years": experience_years,
        "salary": salary,
        "availability": availability,
        "is_vague": is_vague,
        "off_topic": off_topic,
        "missing_answer": missing_answer,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_clarity_high() -> None:
    """Answer with more than 12 words should receive a clarity score of 1.0."""
    ans = _answer(
        original_text=(
            "I have over five years of hands-on experience working with "
            "distributed systems and cloud infrastructure."
        )
    )
    assert len(ans["original_text"].split()) > 12, "Pre-condition: text must exceed 12 words"
    result = score_clarity(ans)
    assert result == 1.0, f"Expected 1.0, got {result}"


def test_clarity_low() -> None:
    """Single-word answer should receive a clarity score of 0.0."""
    ans = _answer(original_text="Yes")
    result = score_clarity(ans)
    assert result == 0.0, f"Expected 0.0, got {result}"


def test_relevance_on_topic() -> None:
    """On-topic answer (off_topic=False) should receive a relevance score of 1.0."""
    ans = _answer(off_topic=False)
    result = score_relevance(ans)
    assert result == 1.0, f"Expected 1.0, got {result}"


def test_relevance_off_topic() -> None:
    """Off-topic answer (off_topic=True) should receive a relevance score of 0.3."""
    ans = _answer(off_topic=True)
    result = score_relevance(ans)
    assert result == 0.3, f"Expected 0.3, got {result}"


def test_relevance_keyword_override() -> None:
    """off_topic=True with non-empty keywords_found should score 0.8, not 0.3."""
    ans = _answer(off_topic=True, keywords_found=["FMEA", "failure mode"])
    result = score_relevance(ans)
    assert result == 0.8, f"Expected 0.8 (keyword override), got {result}"


def test_relevance_off_topic_no_keywords() -> None:
    """off_topic=True with empty keywords_found should still score 0.3."""
    ans = _answer(off_topic=True, keywords_found=[])
    result = score_relevance(ans)
    assert result == 0.3, f"Expected 0.3 (no override), got {result}"


def test_completeness_full() -> None:
    """Answer with keywords, experience years, and known availability → completeness 1.0."""
    ans = _answer(
        keywords_found=["python", "django"],
        experience_years=5,
        availability="Immediate",
    )
    result = score_completeness(ans)
    assert result == 1.0, f"Expected 1.0, got {result}"


def test_consistency_vague() -> None:
    """Vague answer (is_vague=True) should receive a consistency score of 0.3."""
    ans = _answer(is_vague=True, off_topic=False)
    result = score_consistency(ans)
    assert result == 0.3, f"Expected 0.3, got {result}"


def test_consistency_keyword_override() -> None:
    """off_topic=True, is_vague=False, with non-empty keywords_found should score 0.7."""
    ans = _answer(off_topic=True, is_vague=False, keywords_found=["FMEA", "failure mode"])
    result = score_consistency(ans)
    assert result == 0.7, f"Expected 0.7 (keyword override), got {result}"


def test_consistency_vague_overrides_keywords() -> None:
    """is_vague=True should score 0.3 even when off_topic=True and keywords_found is
    non-empty — vagueness is checked first and is not overridden by keyword evidence."""
    ans = _answer(off_topic=True, is_vague=True, keywords_found=["FMEA", "failure mode"])
    result = score_consistency(ans)
    assert result == 0.3, f"Expected 0.3 (vague takes priority), got {result}"


def test_score_answer_structure() -> None:
    """score_answer() must return a dict with the four required top-level keys."""
    ans = _answer()
    result = score_answer(ans)

    required_keys = {"question_id", "scores", "final_score", "weights_used"}
    assert required_keys == required_keys & result.keys(), (
        f"Missing keys in score_answer output: {result}"
    )
    assert result["question_id"] == ans["question_id"]
    assert isinstance(result["final_score"], float)
    score_keys = {"clarity", "relevance", "completeness", "consistency"}
    assert score_keys == score_keys & result["scores"].keys(), (
        f"Missing dimension keys in scores: {result['scores']}"
    )


def test_pipeline_output() -> None:
    """screening_scoring_pipeline() must return a dict with screening_score and decision."""
    answers = [
        _answer(question_id="q1", off_topic=False, is_vague=False, experience_years=4),
        _answer(
            question_id="q2",
            original_text="I am skilled in Python Django REST APIs and microservices.",
            off_topic=False,
            is_vague=False,
            keywords_found=["python", "django"],
            experience_years=2,
            availability="Notice Period",
        ),
    ]
    result = screening_scoring_pipeline(answers)

    assert "screening_score" in result, "'screening_score' key missing from pipeline output"
    assert "decision" in result, "'decision' key missing from pipeline output"
    assert result["decision"] in {"Pass", "Review", "Reject"}, (
        f"Unexpected decision value: {result['decision']!r}"
    )
    assert result["total_questions"] == 2
