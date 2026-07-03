"""
interview_ai/behavior_rules.py

Rule-based stress and surface-contradiction detection for a single
candidate answer.
"""

from __future__ import annotations

from interview_ai.confidence_models import BehaviorFlags
from utils.logger import get_logger

logger = get_logger(__name__)

STRESS_PATTERNS: list[str] = ["not sure", "sorry", "i guess", "maybe"]
# Note: "not sure" and "maybe" also appear in UNCERTAINTY_PHRASES
# (confidence_analyzer.py). This overlap is intentional — they are
# conceptually distinct signals (uncertainty = lack of knowledge
# confidence; stress = nervousness). The overlap is documented in
# DAY36_DECISIONS.md.


def stress_score(text: str) -> float:
    """Score how little stress language an answer contains.

    Args:
        text: The candidate's answer text.

    Returns:
        1.0 if ``text`` is None, empty, or whitespace-only (no stress
        detected in empty input), or if no pattern in
        ``STRESS_PATTERNS`` is present. 0.7 if exactly one pattern is
        present, 0.4 if two or more are present. Higher values
        indicate LESS stress.
    """
    if text is None or not text.strip():
        return 1.0

    text_lower = text.lower()
    count = sum(1 for pattern in STRESS_PATTERNS if pattern in text_lower)

    if count == 0:
        score = 1.0
    elif count == 1:
        score = 0.7
    else:
        score = 0.4

    logger.debug("stress_score count=%d score=%.2f", count, score)
    return score


def detect_surface_contradiction(text: str) -> bool:
    """Detect surface-level linguistic contrast markers in an answer.

    This function is deliberately named with "surface" — it detects
    linguistic contrast markers only ("but", "however" in the text).
    It does NOT detect semantic contradiction: an answer like "I have
    no experience but I led several projects" IS caught; an answer
    that contradicts something said in a different question is NOT
    caught. This distinction is documented in DAY36_DECISIONS.md.

    Args:
        text: The candidate's answer text.

    Returns:
        True if "but" or "however" appears in the lowercased text,
        False otherwise (including for None or empty text).
    """
    if text is None or not text:
        return False

    text_lower = text.lower()
    return "but" in text_lower or "however" in text_lower


def get_behavior_flags(text: str) -> BehaviorFlags:
    """Orchestrate the uncertainty and surface-contradiction rules.

    Args:
        text: The candidate's answer text.

    Returns:
        A ``BehaviorFlags`` instance with ``uncertainty_detected`` set
        to True if any of "maybe", "not sure", "i think", or
        "probably" appear in the lowercased text (False for None,
        empty, or whitespace-only text), and ``contradiction_detected``
        set from ``detect_surface_contradiction``.
    """
    uncertainty_detected = (
        any(
            phrase in text.lower()
            for phrase in ["maybe", "not sure", "i think", "probably"]
        )
        if text and text.strip()
        else False
    )
    contradiction_detected = detect_surface_contradiction(text)

    flags = BehaviorFlags(
        uncertainty_detected=uncertainty_detected,
        contradiction_detected=contradiction_detected,
    )

    logger.debug("get_behavior_flags flags=%s", flags)
    return flags
