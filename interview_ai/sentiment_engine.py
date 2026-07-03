"""
interview_ai/sentiment_engine.py

Lexicon-based sentiment classification of a candidate's answer for the
interview_ai module. POSITIVE_WORDS and NEGATIVE_WORDS are copied BY
VALUE from the post-Day-27 screening_ai/sentiment_engine.py module.
Per interview_ai's module isolation convention, only the values are
copied — this module does not import screening_ai/ under any
circumstances. See DAY36_DECISIONS.md for details.
"""

from __future__ import annotations

from interview_ai.confidence_models import SentimentResult
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


def detect_sentiment(text: str) -> SentimentResult:
    """Detect the overall sentiment of a candidate's answer.

    Counts occurrences of every word/phrase in ``POSITIVE_WORDS`` and
    ``NEGATIVE_WORDS`` within the lowercased text, then classifies the
    overall sentiment based on which count is larger.

    Args:
        text: The candidate's answer text.

    Returns:
        A ``SentimentResult`` with ``sentiment`` (one of "Positive",
        "Negative", or "Neutral") and ``sentiment_score`` (a float
        between 0.0 and 1.0, rounded to 4 decimal places). If ``text``
        is None, empty, or whitespace-only, returns a neutral result
        with ``sentiment_score=0.5``.
    """
    if text is None or not text.strip():
        return SentimentResult(sentiment="Neutral", sentiment_score=0.5)

    text_lower = text.lower()
    pos_count = sum(1 for word in POSITIVE_WORDS if word in text_lower)
    neg_count = sum(1 for word in NEGATIVE_WORDS if word in text_lower)

    if pos_count > neg_count:
        sentiment = "Positive"
        sentiment_score = round(min(pos_count / 5, 1.0), 4)
    elif neg_count > pos_count:
        sentiment = "Negative"
        sentiment_score = round(min(neg_count / 5, 1.0), 4)
    else:
        sentiment = "Neutral"
        sentiment_score = 0.5

    result = SentimentResult(sentiment=sentiment, sentiment_score=sentiment_score)

    logger.info(
        "detect_sentiment pos_count=%d neg_count=%d result=%s",
        pos_count,
        neg_count,
        result,
    )
    return result
