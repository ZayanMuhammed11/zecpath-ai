"""
tests/test_hr_scoring_engine.py

Pure pytest tests for the Day 37 HR interview scoring engine.
No mocking.
"""

from interview_ai.hr_scoring_engine import (
    aggregate_hr_scores,
    get_hr_decision,
    hr_scoring_pipeline,
    score_consistency,
)
from interview_ai.hr_scoring_models import (
    HRAnswerScore,
    HRAnswerScoreBreakdown,
    HRInterviewScore,
)
from interview_ai.hr_weights import get_weights
from interview_ai.interview_models import RoleLevel


def test_empty_answers_returns_zero_score():
    result = hr_scoring_pipeline([])
    assert result.hr_score == 0.0


def test_strong_hire_decision():
    answers = [
        {
            "question_id": "Q1",
            "relevance_score": 1.0,
            "communication_score": 1.0,
            "confidence_score": 1.0,
        }
    ]
    result = hr_scoring_pipeline(answers)
    assert result.decision == "Strong Hire"


def test_reject_decision():
    answers = [
        {
            "question_id": "Q1",
            "relevance_score": 0.0,
            "communication_score": 0.0,
            "confidence_score": 0.0,
        }
    ]
    result = hr_scoring_pipeline(answers)
    assert result.decision == "Reject"


def test_consider_decision():
    answers = [
        {
            "question_id": "Q1",
            "relevance_score": 0.6,
            "communication_score": 0.6,
            "confidence_score": 0.6,
        }
    ]
    result = hr_scoring_pipeline(answers)
    assert result.decision == "Consider"


def test_contradiction_lowers_consistency():
    result = score_consistency(contradiction_detected=True, is_vague=False)
    assert result == 0.3


def test_vague_lowers_consistency():
    result = score_consistency(False, True)
    assert result == 0.6


def test_clean_answer_full_consistency():
    result = score_consistency(False, False)
    assert result == 1.0


def test_role_weights_senior_higher_relevance():
    assert get_weights(RoleLevel.senior)["relevance"] > get_weights(RoleLevel.fresher)["relevance"]


def test_aggregate_normalizes_across_lengths():
    breakdown = HRAnswerScoreBreakdown(
        relevance=1.0, communication=1.0, confidence=1.0, consistency=1.0
    )
    three_answers = [
        HRAnswerScore(question_id="Q1", final_score=80.0, breakdown=breakdown),
        HRAnswerScore(question_id="Q2", final_score=80.0, breakdown=breakdown),
        HRAnswerScore(question_id="Q3", final_score=80.0, breakdown=breakdown),
    ]
    assert aggregate_hr_scores(three_answers) == 80.0


def test_returns_pydantic_model():
    answers = [
        {
            "question_id": "Q1",
            "relevance_score": 0.8,
            "communication_score": 0.7,
            "confidence_score": 0.6,
        }
    ]
    result = hr_scoring_pipeline(answers)
    assert isinstance(result, HRInterviewScore)
    assert isinstance(result.scored_answers[0], HRAnswerScore)
