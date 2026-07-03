"""
interview_ai/hr_weights.py

Role-level scoring weight tables for the Day 37 HR interview scoring
engine. Part of the interview_ai module — fully isolated from
screening_ai/, ats_engine/, and scoring/.

Imports RoleLevel from interview_ai.interview_models — this is an
intra-module import within interview_ai/, which is permitted.
"""

from interview_ai.interview_models import RoleLevel

from utils.logger import get_logger

logger = get_logger(__name__)


ROLE_WEIGHTS: dict[RoleLevel, dict[str, float]] = {
    RoleLevel.fresher: {
        "relevance": 0.25,
        "communication": 0.30,
        "confidence": 0.25,
        "consistency": 0.20,
    },
    RoleLevel.mid: {
        "relevance": 0.30,
        "communication": 0.25,
        "confidence": 0.25,
        "consistency": 0.20,
    },
    RoleLevel.senior: {
        "relevance": 0.35,
        "communication": 0.20,
        "confidence": 0.25,
        "consistency": 0.20,
    },
}

DEFAULT_WEIGHTS = ROLE_WEIGHTS[RoleLevel.fresher]


def get_weights(role_level: RoleLevel) -> dict[str, float]:
    """Return scoring weights for the given role level.

    Args:
        role_level: The candidate's resolved role level.

    Returns:
        A dict mapping dimension name to weight. Falls back to
        DEFAULT_WEIGHTS if role_level is not found in ROLE_WEIGHTS
        (e.g. RoleLevel.all_levels, which has no dedicated weights).
    """
    return ROLE_WEIGHTS.get(role_level, DEFAULT_WEIGHTS)
