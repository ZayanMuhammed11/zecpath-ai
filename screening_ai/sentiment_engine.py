"""Sentiment scoring engine for candidate response analysis.

This module performs a lightweight, lexicon-based sentiment
classification of a candidate's response by counting occurrences of
known positive and negative words.
"""

from __future__ import annotations

from utils.logger import get_logger

logger = get_logger(__name__)

POSITIVE_WORDS = [
    "good",
    "great",
    "confident",
    "skilled",
    "experienced",
    "strong",
    "achieved",
    "success",
]

NEGATIVE_WORDS = [
    "weak",
    "bad",
    "difficult",
    "problem",
    "not sure",
    "struggle",
    "fail",
]


def detect_sentiment(text: str) -> dict:
    """Detect the overall sentiment of a candidate's response.

    Counts occurrences of every word/phrase in ``POSITIVE_WORDS`` and
    ``NEGATIVE_WORDS`` within the lowercased text, then classifies the
    overall sentiment based on which count is larger.

    Args:
        text: The candidate's response text.

    Returns:
        A dictionary with the keys ``sentiment`` (one of ``"Positive"``,
        ``"Negative"``, or ``"Neutral"``) and ``sentiment_score`` (a
        float between 0.0 and 1.0, rounded to 2 decimal places).
    """
    lowered = text.lower()
    pos_count = sum(lowered.count(word) for word in POSITIVE_WORDS)
    neg_count = sum(lowered.count(word) for word in NEGATIVE_WORDS)

    if pos_count > neg_count:
        sentiment = "Positive"
        score = min(pos_count / 5, 1.0)
    elif neg_count > pos_count:
        sentiment = "Negative"
        score = min(neg_count / 5, 1.0)
    else:
        sentiment = "Neutral"
        score = 0.5

    result = {
        "sentiment": sentiment,
        "sentiment_score": round(score, 2),
    }

    logger.info(
        "detect_sentiment pos_count=%d neg_count=%d result=%s",
        pos_count,
        neg_count,
        result,
    )
    return result
