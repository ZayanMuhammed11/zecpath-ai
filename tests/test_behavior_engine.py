"""Tests for the confidence, sentiment, and behavior analysis engines.

No mocking is used; every test exercises real function calls against
plain text inputs.
"""

from __future__ import annotations

from screening_ai.behavior_report import generate_behavior_report
from screening_ai.behavior_rules import detect_contradiction, detect_uncertainty
from screening_ai.confidence_engine import detect_hesitation
from screening_ai.sentiment_engine import detect_sentiment


def test_hesitation_detected() -> None:
    """Text containing 'not sure' and 'maybe' should score above 0.0."""
    text = "I'm not sure, maybe it will work out in the end."
    hesitation = detect_hesitation(text)

    assert hesitation > 0.0


def test_hesitation_clean() -> None:
    """Text with no hesitation phrases should score exactly 0.0."""
    text = "I have five years of experience building backend systems."
    hesitation = detect_hesitation(text)

    assert hesitation == 0.0


def test_sentiment_positive() -> None:
    """Text with 'confident' and 'skilled' should be classified as Positive."""
    result = detect_sentiment("I am confident and skilled in this area.")

    assert result["sentiment"] == "Positive"


def test_sentiment_negative() -> None:
    """Text with 'struggle' and 'fail' should be classified as Negative."""
    result = detect_sentiment("I tend to struggle and sometimes fail under pressure.")

    assert result["sentiment"] == "Negative"


def test_uncertainty_detected() -> None:
    """'I think maybe I can join' should be flagged as uncertain."""
    assert detect_uncertainty("I think maybe I can join") is True


def test_contradiction_detected() -> None:
    """Text containing 'however' should be flagged as a contradiction."""
    text = "I have experience, however I still need more practice."

    assert detect_contradiction(text) is True


def test_behavior_report_structure() -> None:
    """generate_behavior_report should return a dict with the expected top-level keys."""
    report = generate_behavior_report("I have experience leading small teams.")

    assert set(report.keys()) == {
        "confidence",
        "sentiment",
        "behavior_flags",
        "communication_strength",
    }


def test_communication_strength() -> None:
    """A long, confident, positive answer should be classified as Strong."""
    text = (
        "I am confident, skilled, and experienced, and I have achieved "
        "great success while remaining strong under pressure."
    )
    report = generate_behavior_report(text, duration_seconds=8)

    assert report["communication_strength"] == "Strong"
