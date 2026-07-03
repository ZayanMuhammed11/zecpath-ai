"""
tests/test_confidence_analyzer.py

Pytest suite for Day 36 confidence and behavioral signal analysis.
Pure pytest, no mocking, no Redis, no I/O.
"""

from interview_ai.behavior_analyzer import analyze_behavior
from interview_ai.behavior_rules import detect_surface_contradiction, stress_score
from interview_ai.confidence_analyzer import pace_score
from interview_ai.confidence_models import (
    BehaviorFlags,
    ConfidenceBehaviorScore,
    ConfidenceScore,
    SentimentResult,
)
from interview_ai.sentiment_engine import detect_sentiment


def test_empty_text_returns_zero_behavioral_score():
    result = analyze_behavior("")
    assert result.behavioral_score == 0.0


def test_whitespace_only_returns_zero_behavioral_score():
    result = analyze_behavior("   ")
    assert result.behavioral_score == 0.0


def test_confident_answer_scores_high_confidence():
    text = (
        "I led the migration project from start to finish, coordinating "
        "with three teams and delivering ahead of schedule."
    )
    result = analyze_behavior(text, duration_seconds=6.0)
    assert result.confidence.confidence_score > 70


def test_hesitation_words_lower_confidence():
    clean_text = (
        "I led the migration project from start to finish, coordinating "
        "with three teams and delivering ahead of schedule."
    )
    hesitant_text = (
        "I led um the migration project uh from start to finish, um "
        "coordinating with three teams uh and delivering um ahead of uh schedule."
    )

    clean_result = analyze_behavior(clean_text, duration_seconds=6.0)
    hesitant_result = analyze_behavior(hesitant_text, duration_seconds=6.0)

    assert hesitant_result.confidence.confidence_score < clean_result.confidence.confidence_score


def test_pace_score_neutral_on_zero_duration():
    result = pace_score("This is a sample candidate answer.", 0.0)
    assert result == 0.5


def test_positive_sentiment_detected():
    text = "I am confident and have achieved great success in my projects."
    result = detect_sentiment(text)
    assert result.sentiment == "Positive"


def test_negative_sentiment_detected():
    text = "It was a difficult problem and I felt weak, and I might fail."
    result = detect_sentiment(text)
    assert result.sentiment == "Negative"


def test_surface_contradiction_detected():
    text = "I have limited experience but I led several projects successfully."
    assert detect_surface_contradiction(text) is True


def test_stress_score_high_with_no_patterns():
    text = "I led the migration project and delivered ahead of schedule."
    result = stress_score(text)
    assert result == 1.0


def test_returns_pydantic_model():
    result = analyze_behavior("I am confident in my approach.", 5.0)
    assert isinstance(result, ConfidenceBehaviorScore)
    assert isinstance(result.confidence, ConfidenceScore)
    assert isinstance(result.sentiment, SentimentResult)
    assert isinstance(result.behavior_flags, BehaviorFlags)
