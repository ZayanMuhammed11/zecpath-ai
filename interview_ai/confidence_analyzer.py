"""
interview_ai/confidence_analyzer.py

Confidence signal scoring for a single candidate answer, combining
hesitation, repetition, uncertainty, and speaking-pace sub-scores into
a single ConfidenceScore.

HESITATION_WORDS and UNCERTAINTY_PHRASES are copied BY VALUE from the
post-Day-27 screening_ai/confidence_engine.py module (which defines a
single HESITATION_PHRASES list covering filler/uncertainty language).
Per interview_ai's module isolation convention, only the values are
copied — this module does not import screening_ai/ under any
circumstances. See DAY36_DECISIONS.md for details.
"""

from __future__ import annotations

import re

from interview_ai.confidence_models import ConfidenceScore, ConfidenceSignals
from utils.logger import get_logger

logger = get_logger(__name__)

# Filler/hesitation markers — copied by value from
# screening_ai/stt_processor.py (Day 24, confirmed Day 35).
# Distinct from UNCERTAINTY_PHRASES below.
HESITATION_WORDS = [
    "um",
    "uh",
    "like",
    "you know",
    "hmm",
    "basically",
    "actually",
]

UNCERTAINTY_PHRASES = [
    "not sure",
    "maybe",
    "i think",
    "probably",
    "i guess",
    "don't know",
    "depends",
]


def hesitation_score(text: str) -> float:
    """Score how little hesitation/filler language an answer contains.

    Counts occurrences of every word/phrase in ``HESITATION_WORDS``
    using word-boundary regex matching against the lowercased text,
    normalizes the total count, and inverts it so that fewer
    hesitation markers produce a higher score.

    Args:
        text: The candidate's answer text.

    Returns:
        A float between 0.0 and 1.0, rounded to 4 decimal places.
        Higher values indicate LESS hesitation (more confidence).
    """
    lowered = text.lower()
    total_count = 0
    for word in HESITATION_WORDS:
        pattern = r"\b" + re.escape(word) + r"\b"
        total_count += len(re.findall(pattern, lowered))

    normalized = min(total_count / 5, 1.0)
    score = round(1.0 - normalized, 4)

    logger.debug("hesitation_score total_count=%d score=%.4f", total_count, score)
    return score


def repeated_word_score(text: str) -> float:
    """Score how little word repetition an answer contains.

    Args:
        text: The candidate's answer text.

    Returns:
        1.0 if there are no words, or if the repetition ratio (the
        fraction of words that are repeats of an earlier word) is
        below 0.1. 0.7 if the ratio is below 0.3. 0.4 otherwise.
        Higher values indicate LESS repetition.
    """
    words = text.lower().split()
    if len(words) == 0:
        return 1.0

    repetition_ratio = (len(words) - len(set(words))) / len(words)

    if repetition_ratio < 0.1:
        score = 1.0
    elif repetition_ratio < 0.3:
        score = 0.7
    else:
        score = 0.4

    logger.debug(
        "repeated_word_score repetition_ratio=%.4f score=%.2f",
        repetition_ratio,
        score,
    )
    return score


def uncertainty_score(text: str) -> float:
    """Score how little uncertainty language an answer contains.

    Args:
        text: The candidate's answer text.

    Returns:
        1.0 if no phrase in ``UNCERTAINTY_PHRASES`` is present, 0.6 if
        exactly one is present, 0.3 if two or more are present. Higher
        values indicate LESS uncertainty language.
    """
    text_lower = text.lower()
    count = sum(1 for phrase in UNCERTAINTY_PHRASES if phrase in text_lower)

    if count == 0:
        score = 1.0
    elif count == 1:
        score = 0.6
    else:
        score = 0.3

    logger.debug("uncertainty_score count=%d score=%.2f", count, score)
    return score


def pace_score(text: str, duration_seconds: float) -> float:
    """Score a response based on speaking pace (words per second).

    Args:
        text: The candidate's answer text.
        duration_seconds: The duration, in seconds, over which the
            answer was delivered.

    Returns:
        0.5 (a neutral "no data available" fallback) if
        ``duration_seconds`` is less than or equal to 0, to avoid
        unfairly penalizing simulated candidates where no real timing
        data exists yet. Otherwise, 1.0 for an ideal pace of 1.5–3.0
        words per second, 0.7 for a slightly slow (1.0–1.5) or
        slightly fast (3.0–4.0) pace, and 0.4 otherwise.
    """
    if duration_seconds <= 0:
        logger.debug(
            "pace_score non-positive duration_seconds=%.2f; returning neutral 0.5",
            duration_seconds,
        )
        return 0.5

    word_count = len(text.split())
    wps = word_count / duration_seconds

    if 1.5 <= wps <= 3.0:
        score = 1.0
    elif 1.0 <= wps < 1.5:
        score = 0.7
    elif 3.0 < wps <= 4.0:
        score = 0.7
    else:
        score = 0.4

    logger.debug("pace_score wps=%.2f score=%.2f", wps, score)
    return score


def calculate_confidence(text: str, duration_seconds: float = 0.0) -> ConfidenceScore:
    """Calculate an overall confidence score for a candidate's answer.

    Combines the hesitation, repetition, uncertainty, and pace signals
    into a single equally-weighted confidence score on a 0–100 scale.

    Args:
        text: The candidate's answer text.
        duration_seconds: The duration, in seconds, over which the
            answer was delivered. Defaults to 0.0.

    Returns:
        A ``ConfidenceScore`` instance with the overall
        ``confidence_score`` (0.0–100.0) and a nested
        ``ConfidenceSignals`` breakdown. If ``text`` is None, empty,
        or whitespace-only, returns a zeroed-out score and logs a
        warning.
    """
    if text is None or not text.strip():
        logger.warning("calculate_confidence received empty or whitespace-only text")
        return ConfidenceScore(
            confidence_score=0.0,
            signals=ConfidenceSignals(
                hesitation=0.0,
                repetition=0.0,
                uncertainty=0.0,
                pace=0.0,
            ),
        )

    hesitation = hesitation_score(text)
    repetition = repeated_word_score(text)
    uncertainty = uncertainty_score(text)
    pace = pace_score(text, duration_seconds)

    score = (
        hesitation * 0.25
        + repetition * 0.25
        + uncertainty * 0.25
        + pace * 0.25
    )
    confidence_score = round(score * 100, 2)

    logger.info("calculate_confidence confidence_score=%.2f", confidence_score)

    return ConfidenceScore(
        confidence_score=confidence_score,
        signals=ConfidenceSignals(
            hesitation=hesitation,
            repetition=repetition,
            uncertainty=uncertainty,
            pace=pace,
        ),
    )
