"""Aggregate behavior report combining confidence, sentiment, and rule-based signals.

This module ties together ``confidence_engine``, ``sentiment_engine``,
and ``behavior_rules`` into a single, consolidated behavior report for
a candidate's answer, along with an overall communication strength
classification.
"""

from __future__ import annotations

from screening_ai.behavior_rules import detect_contradiction, detect_uncertainty
from screening_ai.confidence_engine import calculate_confidence
from utils.logger import get_logger
from screening_ai.sentiment_engine import detect_sentiment

logger = get_logger(__name__)


def calculate_strength(confidence_score: float, sentiment_score: float) -> str:
    """Classify overall communication strength from confidence and sentiment.

    Combines the two scores as
    ``(confidence_score * 0.6) + (sentiment_score * 0.4)``.

    Args:
        confidence_score: The candidate's confidence score (0.0-1.0).
        sentiment_score: The candidate's sentiment score (0.0-1.0).

    Returns:
        ``"Strong"`` if the combined score is greater than or equal to
        0.75, ``"Moderate"`` if it is greater than or equal to 0.50,
        otherwise ``"Weak"``.
    """
    combined = (confidence_score * 0.6) + (sentiment_score * 0.4)

    if combined >= 0.75:
        strength = "Strong"
    elif combined >= 0.50:
        strength = "Moderate"
    else:
        strength = "Weak"

    logger.debug(
        "calculate_strength combined=%.2f strength=%s", combined, strength
    )
    return strength


def generate_behavior_report(answer_text: str, duration_seconds: int = 10) -> dict:
    """Generate a full behavior report for a candidate's answer.

    Combines confidence scoring, sentiment analysis, and rule-based
    behavior flags into a single report, along with an overall
    communication strength classification.

    Args:
        answer_text: The candidate's response text.
        duration_seconds: The duration, in seconds, over which the
            response was delivered. Defaults to 10.

    Returns:
        A dictionary with the keys ``confidence`` (the result of
        ``calculate_confidence``), ``sentiment`` (the result of
        ``detect_sentiment``), ``behavior_flags`` (a dictionary with
        ``uncertainty`` and ``contradiction`` booleans), and
        ``communication_strength`` (one of ``"Strong"``, ``"Moderate"``,
        or ``"Weak"``).
    """
    confidence = calculate_confidence(answer_text, duration_seconds)
    sentiment = detect_sentiment(answer_text)

    report = {
        "confidence": confidence,
        "sentiment": sentiment,
        "behavior_flags": {
            "uncertainty": detect_uncertainty(answer_text),
            "contradiction": detect_contradiction(answer_text),
        },
        "communication_strength": calculate_strength(
            confidence["confidence_score"],
            sentiment["sentiment_score"],
        ),
    }

    logger.info(
        "generate_behavior_report communication_strength=%s",
        report["communication_strength"],
    )
    return report
