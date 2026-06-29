"""
tests/test_answer_engine.py

8 pytest tests for the Day 25 Answer Intent & Understanding Engine.

No mocking required — no Redis or external calls are made.
"""

import pytest

from screening_ai.answer_engine import (
    classify_intent,
    extract_experience_years,
    extract_salary,
    extract_availability,
    is_vague,
    process_answer,
    process_answers_batch,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_batch() -> list[dict]:
    """Return a deterministic 3-item batch for batch-related tests."""
    return [
        {
            "question_id": "q1",
            "answer_text": "I have 5 years of experience in Python and Django.",
            "expected_keywords": ["python", "django"],
            "expected_intent": "experience",
        },
        {
            "question_id": "q2",
            "answer_text": "My salary expectation is 12 lpa.",
            "expected_keywords": ["salary"],
            "expected_intent": "salary",
        },
        {
            "question_id": "q3",
            "answer_text": "I can join immediately after the offer.",
            "expected_keywords": ["join", "immediate"],
            "expected_intent": "availability",
        },
    ]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_intent_classification_experience() -> None:
    """Sentence describing work history should classify as 'experience'."""
    text = "I have 5 years of experience in quality engineering."
    result = classify_intent(text)
    assert result == "experience", f"Expected 'experience', got {result!r}"


def test_intent_classification_skills() -> None:
    """Sentence describing technical competencies should classify as 'skills'."""
    text = "I am proficient in FMEA and SPC tools."
    result = classify_intent(text)
    assert result == "skills", f"Expected 'skills', got {result!r}"


def test_extract_experience_years() -> None:
    """'7 years of experience' should return 7."""
    text = "I have 7 years of experience in the automotive sector."
    result = extract_experience_years(text)
    assert result == 7, f"Expected 7, got {result}"


def test_extract_salary() -> None:
    """Salary mention '8 lpa' should be extracted as a non-None string."""
    text = "My expectation is 8 lpa for this role."
    result = extract_salary(text)
    assert result is not None, "Expected a salary match, got None"
    assert "8" in result, f"Extracted salary {result!r} should contain '8'"


def test_extract_availability_immediate() -> None:
    """'I can join immediately' should return 'Immediate'."""
    text = "I can join immediately after receiving the offer letter."
    result = extract_availability(text)
    assert result == "Immediate", f"Expected 'Immediate', got {result!r}"


def test_vague_detection() -> None:
    """Answer containing hedging phrases should be flagged as vague."""
    text = "I think maybe I have some experience in this area."
    result = is_vague(text)
    assert result is True, "Expected is_vague=True for hedging language"


def test_off_topic_detection() -> None:
    """Answer about salary when expected_intent='experience' should be off-topic."""
    result = process_answer(
        question_id="q_off",
        answer_text="My current CTC is 10 lpa and I expect 14 lpa.",
        expected_keywords=["experience", "years"],
        expected_intent="experience",
    )
    assert result["off_topic"] is True, (
        f"Expected off_topic=True, got off_topic={result['off_topic']}, "
        f"intent={result['intent']!r}"
    )


def test_batch_processing() -> None:
    """process_answers_batch should return one result per input, each with 'intent'."""
    batch = _make_batch()
    results = process_answers_batch(batch)

    assert len(results) == 3, f"Expected 3 results, got {len(results)}"
    for r in results:
        assert "intent" in r, f"'intent' key missing from result: {r}"
