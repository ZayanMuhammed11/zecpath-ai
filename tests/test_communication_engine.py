"""
tests/test_communication_engine.py

Pytest test suite for interview_ai/communication_engine.py.

Pure computation tests — no mocking, no I/O, no Redis.
All inputs are plain Python strings; assertions verify numeric thresholds
and Pydantic model types only.
"""

import pytest

from interview_ai.communication_engine import (
    calculate_communication_score,
    filler_penalty,
    get_communication_level,
    score_fluency,
    score_grammar,
    score_structure,
    score_vocabulary,
)
from interview_ai.communication_models import CommunicationScore, CommunicationScoreBreakdown


# ---------------------------------------------------------------------------
# calculate_communication_score — empty / whitespace input
# ---------------------------------------------------------------------------


def test_empty_text_returns_zero_score() -> None:
    """Empty string must produce communication_score=0.0 and level='Poor'."""
    result = calculate_communication_score("")
    assert result.communication_score == 0.0
    assert result.level == "Poor"


def test_whitespace_only_text_returns_zero_score() -> None:
    """Whitespace-only string must produce communication_score=0.0 and level='Poor'."""
    result = calculate_communication_score("   ")
    assert result.communication_score == 0.0
    assert result.level == "Poor"


# ---------------------------------------------------------------------------
# calculate_communication_score — high and low quality answers
# ---------------------------------------------------------------------------


def test_strong_answer_scores_high() -> None:
    """A multi-sentence, grammatically correct, structure-keyword-rich answer should exceed 80."""
    text = (
        "I work best in collaborative environments because I value open communication. "
        "For example, in my previous role I led a successful team project that delivered "
        "results ahead of schedule. Additionally, clear feedback loops help everyone "
        "improve their performance consistently."
    )
    result = calculate_communication_score(text)
    assert result.communication_score > 80
    assert result.level in ("Excellent", "Good")


def test_weak_answer_scores_low() -> None:
    """A short, filler-heavy, unpunctuated fragment must score below 50 with level 'Poor'."""
    result = calculate_communication_score("um uh yeah")
    assert result.communication_score < 50
    assert result.level == "Poor"


def test_filler_words_reduce_score() -> None:
    """Inserting filler words into an otherwise clean sentence must lower the communication score."""
    clean_text = (
        "I have extensive experience in software development and team leadership."
    )
    filler_text = (
        "I have um extensive experience in software development "
        "and uh you know team leadership."
    )
    clean_result = calculate_communication_score(clean_text)
    filler_result = calculate_communication_score(filler_text)
    assert filler_result.communication_score < clean_result.communication_score


# ---------------------------------------------------------------------------
# score_vocabulary — short-text cap
# ---------------------------------------------------------------------------


def test_short_text_vocabulary_capped() -> None:
    """score_vocabulary on a 2-word fully-unique string must return at most 0.5."""
    result = score_vocabulary("hello world")
    assert result <= 0.5


# ---------------------------------------------------------------------------
# score_structure — keyword detection
# ---------------------------------------------------------------------------


def test_structure_keyword_detected() -> None:
    """score_structure must return 1.0 when the keyword 'because' appears in the text."""
    result = score_structure("I chose this approach because it produces better results.")
    assert result == 1.0


# ---------------------------------------------------------------------------
# score_grammar — high and low quality
# ---------------------------------------------------------------------------


def test_grammar_score_high_quality() -> None:
    """A properly capitalised, terminated, and reasonably long sentence must score >= 0.8."""
    text = "The candidate demonstrated excellent communication skills throughout the interview."
    result = score_grammar(text)
    assert result >= 0.8


def test_grammar_score_low_quality() -> None:
    """A single lowercase, unpunctuated word must score <= 0.5."""
    result = score_grammar("bad")
    assert result <= 0.5


# ---------------------------------------------------------------------------
# get_communication_level — boundary values
# ---------------------------------------------------------------------------


def test_communication_level_boundaries() -> None:
    """get_communication_level must return the correct label at every defined boundary."""
    assert get_communication_level(85.0) == "Excellent"
    assert get_communication_level(84.99) == "Good"
    assert get_communication_level(70.0) == "Good"
    assert get_communication_level(69.99) == "Average"
    assert get_communication_level(50.0) == "Average"
    assert get_communication_level(49.99) == "Poor"


# ---------------------------------------------------------------------------
# calculate_communication_score — return type
# ---------------------------------------------------------------------------


def test_returns_pydantic_model() -> None:
    """calculate_communication_score must return a CommunicationScore whose breakdown
    is a CommunicationScoreBreakdown instance."""
    result = calculate_communication_score("I believe this approach works well.")
    assert isinstance(result, CommunicationScore)
    assert isinstance(result.breakdown, CommunicationScoreBreakdown)
