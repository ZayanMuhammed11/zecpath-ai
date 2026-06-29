"""Confidence scoring engine for candidate response analysis.

This module scores how confidently a candidate delivered a response
during a screening interview, based on three signals:

- Hesitation language (filler/uncertainty phrases).
- Response length (word count).
- Speaking pace (words per second).

These signals are combined into a single weighted confidence score by
``calculate_confidence``.
"""

from __future__ import annotations

from utils.logger import get_logger

logger = get_logger(__name__)

HESITATION_PHRASES = [
    "not sure",
    "maybe",
    "i think",
    "probably",
    "i guess",
    "don't know",
    "depends",
]

IDEAL_WPS_MIN = 1.5
IDEAL_WPS_MAX = 3.0


def detect_hesitation(text: str) -> float:
    """Detect hesitation language in a candidate's response.

    Counts the total number of occurrences of every phrase in
    ``HESITATION_PHRASES`` within the lowercased text, then normalizes
    that count into a 0.0-1.0 score.

    Args:
        text: The candidate's response text.

    Returns:
        A float between 0.0 and 1.0, computed as
        ``min(count / 5, 1.0)``, where ``count`` is the total number of
        hesitation phrase occurrences found.
    """
    lowered = text.lower()
    count = sum(lowered.count(phrase) for phrase in HESITATION_PHRASES)
    score = min(count / 5, 1.0)

    logger.debug("detect_hesitation count=%d score=%.2f", count, score)
    return score


def response_length_score(text: str) -> float:
    """Score a response based on its word count.

    Args:
        text: The candidate's response text.

    Returns:
        1.0 if the response has more than 12 words, 0.7 if more than 6
        words, 0.4 if more than 2 words, otherwise 0.1.
    """
    word_count = len(text.split())

    if word_count > 12:
        score = 1.0
    elif word_count > 6:
        score = 0.7
    elif word_count > 2:
        score = 0.4
    else:
        score = 0.1

    logger.debug(
        "response_length_score word_count=%d score=%.2f", word_count, score
    )
    return score


def pace_score(text: str, duration_seconds: int) -> float:
    """Score a response based on speaking pace (words per second).

    Args:
        text: The candidate's response text.
        duration_seconds: The duration, in seconds, over which the
            response was delivered.

    Returns:
        0.0 if ``duration_seconds`` is less than or equal to 0.
        Otherwise, 1.0 if the words-per-second rate falls within
        ``[IDEAL_WPS_MIN, IDEAL_WPS_MAX]``; 0.7 if it falls within
        ``[1.0, IDEAL_WPS_MIN)`` or ``(IDEAL_WPS_MAX, 4.0]``; and 0.4
        otherwise.
    """
    if duration_seconds <= 0:
        logger.debug(
            "pace_score non-positive duration_seconds=%.2f; returning 0.0",
            duration_seconds,
        )
        return 0.0

    word_count = len(text.split())
    wps = word_count / duration_seconds

    if IDEAL_WPS_MIN <= wps <= IDEAL_WPS_MAX:
        score = 1.0
    elif (1.0 <= wps < IDEAL_WPS_MIN) or (IDEAL_WPS_MAX < wps <= 4.0):
        score = 0.7
    else:
        score = 0.4

    logger.debug("pace_score wps=%.2f score=%.2f", wps, score)
    return score


def calculate_confidence(text: str, duration_seconds: int = 10) -> dict:
    """Calculate an overall confidence score for a candidate's response.

    Combines the hesitation, response length, and pace signals into a
    single weighted confidence score:
    ``(length * 0.4) + (pace * 0.4) + ((1 - hesitation) * 0.2)``.

    Args:
        text: The candidate's response text.
        duration_seconds: The duration, in seconds, over which the
            response was delivered. Defaults to 10.

    Returns:
        A dictionary with the overall ``confidence_score`` and a nested
        ``signals`` dictionary containing the individual ``hesitation``,
        ``length_score``, and ``pace_score`` components, all rounded to
        2 decimal places.
    """
    hesitation = detect_hesitation(text)
    length = response_length_score(text)
    pace = pace_score(text, duration_seconds)

    confidence = (length * 0.4) + (pace * 0.4) + ((1 - hesitation) * 0.2)

    result = {
        "confidence_score": round(confidence, 2),
        "signals": {
            "hesitation": round(hesitation, 2),
            "length_score": round(length, 2),
            "pace_score": round(pace, 2),
        },
    }

    logger.info("calculate_confidence result=%s", result)
    return result
