"""
interview_ai/scenario_evaluator.py

Ratio-based scenario pattern matching for situational_judgment aptitude
questions.
Part of Zecpath AI — Day 38, Sprint 4.

Replaces the manager sample's binary all/some/none tiers with a
continuous match_ratio = matched_patterns / total_patterns, consistent
with the graduated scoring philosophy used throughout aptitude_scoring.py
and communication_engine.py.

SCENARIO_PATTERNS is an extensible registry so future days can add new
scenario types without touching evaluate_scenario() itself.
"""

import re
from typing import List

from utils.logger import get_logger

from interview_ai.aptitude_models import ScenarioEvaluation

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Scenario pattern registry
# ---------------------------------------------------------------------------

# Extensible registry keyed by scenario_type. Each value is the list of
# expected behavioral pattern keywords for that scenario. Seeded with the
# 3 scenario types used in data/aptitude_questions.json; future days can
# append new entries here without changing evaluate_scenario().
SCENARIO_PATTERNS: dict[str, List[str]] = {
    "deadline_pressure": ["prioritize", "plan", "execute", "communicate"],
    "team_conflict": ["listen", "understand", "resolve", "communicate"],
    "learning_agility": ["research", "practice", "apply", "ask"],
}


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------


def evaluate_scenario(text: str, scenario_type: str) -> ScenarioEvaluation:
    """
    Evaluate a candidate's answer against the expected behavioral pattern
    keywords for a given scenario_type using ratio-based matching.

    Uses word-boundary regex matching so partial-word false positives
    (e.g. "resolved" matching "resolve") are still counted as a match on
    the pattern's stem, consistent with the aptitude scoring markers'
    substring-safe intent.

    Unknown scenario_type values do not raise — they are logged as a
    warning and return a zero-ratio, empty-match evaluation, so callers
    (e.g. calculate_aptitude_score) can safely blend the result without
    special-casing failure.

    Args:
        text: Cleaned candidate answer text to evaluate.
        scenario_type: Key into SCENARIO_PATTERNS identifying which
            pattern set to match against.

    Returns:
        A ScenarioEvaluation with match_ratio rounded to 4 decimal
        places, the list of matched pattern keywords, and the total
        pattern count for the scenario_type.
    """
    logger.debug(
        "evaluate_scenario called with scenario_type=%r, text=%r",
        scenario_type,
        text,
    )

    patterns = SCENARIO_PATTERNS.get(scenario_type)
    if patterns is None:
        logger.warning(
            "evaluate_scenario: unknown scenario_type='%s'; returning "
            "zero match_ratio.",
            scenario_type,
        )
        return ScenarioEvaluation(
            scenario_type=scenario_type,
            match_ratio=0.0,
            matched_patterns=[],
            total_patterns=0,
        )

    text_lower = text.lower() if text else ""
    matched: List[str] = []
    for pattern in patterns:
        regex = r"\b" + re.escape(pattern) + r"\w*\b"
        if re.search(regex, text_lower):
            matched.append(pattern)

    total_patterns = len(patterns)
    match_ratio = round(len(matched) / total_patterns, 4) if total_patterns else 0.0

    logger.info(
        "evaluate_scenario: scenario_type='%s' -> match_ratio=%.4f "
        "(%d/%d patterns matched).",
        scenario_type,
        match_ratio,
        len(matched),
        total_patterns,
    )

    return ScenarioEvaluation(
        scenario_type=scenario_type,
        match_ratio=match_ratio,
        matched_patterns=matched,
        total_patterns=total_patterns,
    )
