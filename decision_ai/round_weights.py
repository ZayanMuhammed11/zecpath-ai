"""Role-based weight definitions for the unified scoring engine.

Each role level maps to a dict of base weights for the five rounds
(ats, screening, hr, technical, machine_test). These are the weights
used before any missing-round redistribution happens in
unified_scoring_engine.redistribute_weights().

Day 51 update: extended from a 3-round table (ats, screening, hr) to a
5-round table that also includes technical and machine_test. See
DAY51_DECISIONS.md for the rationale, including the deliberate
inclusion of machine_test_ai's domain-mismatched scores.
"""

from typing import Dict

from decision_ai.decision_models import RoleLevel

ROLE_WEIGHTS: Dict[RoleLevel, Dict[str, float]] = {
    RoleLevel.fresher: {
        "ats": 0.15, "screening": 0.20, "hr": 0.25,
        "technical": 0.20, "machine_test": 0.20,
    },
    RoleLevel.mid: {
        "ats": 0.20, "screening": 0.15, "hr": 0.25,
        "technical": 0.25, "machine_test": 0.15,
    },
    RoleLevel.senior: {
        "ats": 0.20, "screening": 0.10, "hr": 0.25,
        "technical": 0.30, "machine_test": 0.15,
    },
}

DEFAULT_WEIGHTS: Dict[str, float] = ROLE_WEIGHTS[RoleLevel.mid]


def get_weights(role_level: RoleLevel) -> Dict[str, float]:
    """Return a copy of the base weights for the given role level.

    Falls back to DEFAULT_WEIGHTS if role_level is not present in
    ROLE_WEIGHTS. Always returns a copy so callers cannot mutate the
    module-level source of truth.
    """
    weights = ROLE_WEIGHTS.get(role_level, DEFAULT_WEIGHTS)
    return dict(weights)


# Startup-time sanity check (not a runtime exception raised on import in a
# way that would crash unrelated code paths, but an assertion that fails
# loudly and immediately if the weight tables are ever edited incorrectly).
# This is intentionally ALSO covered by an explicit pytest test
# (test_every_role_weight_set_sums_to_one) rather than relying on this
# assertion alone.
for _role, _weights in ROLE_WEIGHTS.items():
    _total = sum(_weights.values())
    assert abs(_total - 1.0) < 1e-6, (
        f"ROLE_WEIGHTS[{_role!r}] must sum to 1.0, got {_total}"
    )
