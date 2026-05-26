"""
Role-based scoring weight registry for the Zecpath ATS Engine.
Provides per-role weight profiles across skills, experience,
education, and semantic similarity dimensions.
"""

from utils.logger import get_logger

logger = get_logger(__name__)


# ─── Role Weight Registry ──────────────────────────────────────────────────────

ROLE_WEIGHTS: dict[str, dict[str, float]] = {
    "quality engineer": {
        "skills": 0.35,
        "experience": 0.30,
        "education": 0.10,
        "semantic": 0.25,
    },
    "qa engineer": {
        "skills": 0.35,
        "experience": 0.30,
        "education": 0.10,
        "semantic": 0.25,
    },
    "quality manager": {
        "skills": 0.30,
        "experience": 0.35,
        "education": 0.10,
        "semantic": 0.25,
    },
    "process engineer": {
        "skills": 0.35,
        "experience": 0.30,
        "education": 0.10,
        "semantic": 0.25,
    },
    "backend developer": {
        "skills": 0.40,
        "experience": 0.30,
        "education": 0.10,
        "semantic": 0.20,
    },
    "data scientist": {
        "skills": 0.35,
        "experience": 0.25,
        "education": 0.20,
        "semantic": 0.20,
    },
    "devops engineer": {
        "skills": 0.40,
        "experience": 0.30,
        "education": 0.10,
        "semantic": 0.20,
    },
}

DEFAULT_WEIGHTS: dict[str, float] = {
    "skills": 0.35,
    "experience": 0.25,
    "education": 0.15,
    "semantic": 0.25,
}


# ─── Public Function ───────────────────────────────────────────────────────────

def get_role_weights(job_title: str) -> dict[str, float]:
    """
    Return a scoring weight profile for the given job title.

    Performs a case-insensitive exact match against ROLE_WEIGHTS keys.
    Falls back to DEFAULT_WEIGHTS when no match is found and logs a
    debug message so callers can detect unexpected role strings.

    Always returns a shallow copy so callers cannot mutate the registry.

    Args:
        job_title: The job role string, e.g. ``"Quality Engineer"``.

    Returns:
        Dict with keys ``skills``, ``experience``, ``education``,
        ``semantic`` — floats summing to 1.0.
    """
    normalised = job_title.lower().strip()
    weights = ROLE_WEIGHTS.get(normalised)

    if weights is None:
        logger.debug(
            "No role weight profile found for '%s' — falling back to DEFAULT_WEIGHTS.",
            job_title,
        )
        return dict(DEFAULT_WEIGHTS)

    return dict(weights)