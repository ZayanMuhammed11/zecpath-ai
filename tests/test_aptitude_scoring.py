"""
tests/test_aptitude_scoring.py

Pytest test suite for interview_ai/aptitude_scoring.py and
interview_ai/scenario_evaluator.py.

Pure computation tests — no mocking, no I/O, no Redis.
All inputs are plain Python strings; assertions verify numeric
thresholds and Pydantic model types only.
"""

import pytest

from interview_ai.aptitude_models import AptitudeScore, AptitudeScoreBreakdown
from interview_ai.aptitude_scoring import (
    calculate_aptitude_score,
    get_aptitude_level,
    score_decision_quality,
    score_problem_solving,
    score_structure,
)


# ---------------------------------------------------------------------------
# calculate_aptitude_score — empty / whitespace input
# ---------------------------------------------------------------------------


def test_empty_text_returns_zero_score() -> None:
    """Empty string must produce aptitude_score=0.0 with a zeroed breakdown."""
    result = calculate_aptitude_score("")
    assert result.aptitude_score == 0.0
    assert result.breakdown.structure == 0.0
    assert result.breakdown.problem_solving == 0.0
    assert result.breakdown.decision_quality == 0.0
    assert result.scenario_evaluation is None


def test_whitespace_only_text_returns_zero_score() -> None:
    """Whitespace-only string must produce aptitude_score=0.0."""
    result = calculate_aptitude_score("   ")
    assert result.aptitude_score == 0.0


def test_none_text_returns_zero_score() -> None:
    """None input must produce aptitude_score=0.0 without raising."""
    result = calculate_aptitude_score(None)
    assert result.aptitude_score == 0.0


# ---------------------------------------------------------------------------
# calculate_aptitude_score — strong vs weak answers
# ---------------------------------------------------------------------------


def test_strong_answer_scores_above_70() -> None:
    """A reasoning-marker-rich, problem-solving-oriented answer should score above 70."""
    text = (
        "First, I would consider the root cause because the deadline is at risk. "
        "Then I would analyze the available options and prioritize the highest-impact "
        "fix. My approach is to build a clear plan, evaluate each solution, and "
        "therefore decide on the method that gets us to a working release as a result."
    )
    result = calculate_aptitude_score(text)
    assert result.aptitude_score > 70


def test_weak_short_answer_scores_below_50() -> None:
    """A short answer with no markers must score below 50."""
    result = calculate_aptitude_score("I don't know, maybe fix it.")
    assert result.aptitude_score < 50


# ---------------------------------------------------------------------------
# score_structure — marker detection
# ---------------------------------------------------------------------------


def test_score_structure_detects_markers() -> None:
    """score_structure must return 1.0 when 4+ distinct REASONING_MARKERS are present."""
    text = "First I checked the logs, then I found the cause, because the job failed, so that we could fix it."
    result = score_structure(text)
    assert result == 1.0


def test_score_structure_no_markers_is_zero() -> None:
    """score_structure must return 0.0 when no REASONING_MARKERS are present."""
    result = score_structure("I would just try things until it works.")
    assert result == 0.0


# ---------------------------------------------------------------------------
# score_problem_solving — length-floor cap
# ---------------------------------------------------------------------------


def test_score_problem_solving_length_floor_cap() -> None:
    """A short answer (< 6 words) containing markers must still be capped at 0.5."""
    result = score_problem_solving("My plan is the solution.")
    assert result <= 0.5


def test_score_problem_solving_long_answer_exceeds_floor() -> None:
    """A longer answer (>= 6 words) with multiple markers can exceed the 0.5 floor."""
    text = (
        "My approach is to build a clear plan, choose the right method, "
        "and find the best solution to solve this properly."
    )
    result = score_problem_solving(text)
    assert result > 0.5


# ---------------------------------------------------------------------------
# score_decision_quality — marker detection
# ---------------------------------------------------------------------------


def test_score_decision_quality_detects_markers() -> None:
    """score_decision_quality must return a positive ratio when markers are present."""
    text = "I would consider the tradeoffs, analyze the data, and evaluate each option before I decide."
    result = score_decision_quality(text)
    assert result > 0.0


def test_score_decision_quality_no_markers_is_zero() -> None:
    """score_decision_quality must return 0.0 when no DECISION_MARKERS are present."""
    result = score_decision_quality("I would just pick one and move on.")
    assert result == 0.0


# ---------------------------------------------------------------------------
# get_aptitude_level — boundary values
# ---------------------------------------------------------------------------


def test_aptitude_level_boundaries() -> None:
    """get_aptitude_level must return the correct label at every defined boundary."""
    assert get_aptitude_level(85.0) == "Excellent"
    assert get_aptitude_level(84.99) == "Good"
    assert get_aptitude_level(70.0) == "Good"
    assert get_aptitude_level(69.99) == "Average"
    assert get_aptitude_level(50.0) == "Average"
    assert get_aptitude_level(49.99) == "Poor"


# ---------------------------------------------------------------------------
# scenario blending
# ---------------------------------------------------------------------------


def test_scenario_blending_changes_final_score() -> None:
    """Providing a scenario_type must change the final score relative to the
    no-scenario baseline, since match_ratio is blended into the result."""
    text = (
        "First I would prioritize the most critical tasks, then plan the "
        "remaining work, execute quickly, and communicate status because "
        "the deadline is close."
    )
    baseline = calculate_aptitude_score(text)
    with_scenario = calculate_aptitude_score(text, scenario_type="deadline_pressure")
    assert baseline.aptitude_score != with_scenario.aptitude_score
    assert with_scenario.scenario_evaluation is not None
    assert with_scenario.scenario_evaluation.scenario_type == "deadline_pressure"


def test_unknown_scenario_type_does_not_raise() -> None:
    """An unknown scenario_type must not raise and must produce a zero match_ratio."""
    text = "First I would plan the approach and then execute it."
    result = calculate_aptitude_score(text, scenario_type="not_a_real_scenario")
    assert result.scenario_evaluation is not None
    assert result.scenario_evaluation.match_ratio == 0.0
    assert result.scenario_evaluation.matched_patterns == []
    assert result.scenario_evaluation.total_patterns == 0


# ---------------------------------------------------------------------------
# return type
# ---------------------------------------------------------------------------


def test_returns_pydantic_model() -> None:
    """calculate_aptitude_score must return an AptitudeScore whose breakdown
    is an AptitudeScoreBreakdown instance."""
    result = calculate_aptitude_score("First I would analyze the problem, then plan a solution.")
    assert isinstance(result, AptitudeScore)
    assert isinstance(result.breakdown, AptitudeScoreBreakdown)
