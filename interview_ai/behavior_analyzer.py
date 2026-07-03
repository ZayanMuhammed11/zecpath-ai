"""
interview_ai/behavior_analyzer.py

Top-level aggregation of confidence, sentiment, and behavior signals
into a single ConfidenceBehaviorScore for a candidate's answer.

Only imports from interview_ai files created in the same Day 36
batch (confidence_models, confidence_analyzer, sentiment_engine,
behavior_rules) — no other interview_ai/ imports.
"""

from __future__ import annotations

from interview_ai.behavior_rules import get_behavior_flags, stress_score
from interview_ai.confidence_analyzer import calculate_confidence
from interview_ai.confidence_models import (
    BehaviorFlags,
    ConfidenceBehaviorScore,
    ConfidenceScore,
    ConfidenceSignals,
    SentimentResult,
)
from interview_ai.sentiment_engine import detect_sentiment
from utils.logger import get_logger

logger = get_logger(__name__)


def analyze_behavior(text: str, duration_seconds: float = 0.0) -> ConfidenceBehaviorScore:
    """Aggregate confidence, sentiment, and behavior signals for an answer.

    Combines a ``ConfidenceScore``, a ``SentimentResult``, and
    ``BehaviorFlags`` into a single ``ConfidenceBehaviorScore``, with
    a unit-consistent final ``behavioral_score`` on a 0–100 scale.

    Args:
        text: The candidate's answer text.
        duration_seconds: The duration, in seconds, over which the
            answer was delivered. Defaults to 0.0.

    Returns:
        A fully populated ``ConfidenceBehaviorScore``. If ``text`` is
        None, empty, or whitespace-only, returns a zeroed-out,
        neutral-sentiment, no-stress result with
        ``behavioral_score=0.0`` and logs a warning.
    """
    if text is None or not text.strip():
        logger.warning("analyze_behavior received empty or whitespace-only text")
        return ConfidenceBehaviorScore(
            confidence=ConfidenceScore(
                confidence_score=0.0,
                signals=ConfidenceSignals(
                    hesitation=0.0,
                    repetition=0.0,
                    uncertainty=0.0,
                    pace=0.0,
                ),
            ),
            sentiment=SentimentResult(sentiment="Neutral", sentiment_score=0.5),
            behavior_flags=BehaviorFlags(
                uncertainty_detected=False,
                contradiction_detected=False,
            ),
            stress_score=1.0,
            behavioral_score=0.0,
        )

    confidence = calculate_confidence(text, duration_seconds)
    sentiment = detect_sentiment(text)
    flags = get_behavior_flags(text)
    stress = stress_score(text)

    # UNIT-CONSISTENT AGGREGATION:
    # All inputs normalized to 0-100 scale before combining.
    # confidence.confidence_score is already 0-100.
    # sentiment.sentiment_score is 0-1, multiply by 100.
    # stress is 0-1, multiply by 100.
    behavioral_score = round(
        confidence.confidence_score * 0.5
        + sentiment.sentiment_score * 100 * 0.2
        + stress * 100 * 0.3,
        2,
    )

    logger.info("analyze_behavior behavioral_score=%.2f", behavioral_score)

    return ConfidenceBehaviorScore(
        confidence=confidence,
        sentiment=sentiment,
        behavior_flags=flags,
        stress_score=stress,
        behavioral_score=behavioral_score,
    )
