"""Rule-based behavior signal detection for candidate responses.

This module provides simple, deterministic phrase-matching rules used
to flag uncertainty and contradiction in a candidate's response text.
"""

from __future__ import annotations

from utils.logger import get_logger

logger = get_logger(__name__)

UNCERTAINTY_PHRASES = ["maybe", "not sure", "i think", "probably", "i guess"]
CONTRADICTION_MARKERS = ["but", "however", "although", "yet", "despite"]


def detect_uncertainty(text: str) -> bool:
    """Detect whether a response contains uncertainty language.

    Args:
        text: The candidate's response text.

    Returns:
        True if any phrase in ``UNCERTAINTY_PHRASES`` is found in the
        lowercased text, otherwise False.
    """
    lowered = text.lower()
    found = any(phrase in lowered for phrase in UNCERTAINTY_PHRASES)

    logger.debug("detect_uncertainty found=%s", found)
    return found


def detect_contradiction(text: str) -> bool:
    """Detect whether a response contains contradiction markers.

    Args:
        text: The candidate's response text.

    Returns:
        True if any marker in ``CONTRADICTION_MARKERS`` is found in the
        lowercased text, otherwise False.
    """
    lowered = text.lower()
    found = any(marker in lowered for marker in CONTRADICTION_MARKERS)

    logger.debug("detect_contradiction found=%s", found)
    return found
