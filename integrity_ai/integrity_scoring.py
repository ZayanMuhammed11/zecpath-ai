"""
integrity_ai/integrity_scoring.py

Day 49 integrity signal-to-risk-score mapping engine. Combines four
caller-supplied raw event counts (tab_switch_count, focus_loss_count,
external_voice_count, gaze_deviation_count) into a single weighted
integrity_score, plus deterministic threshold-based warnings.

IMPORTANT: this module contains NO browser tab-switch detection, NO
screen focus tracking, NO audio voice detection, and NO gaze tracking
logic. Every numeric input to every function in this module is 100%
CALLER-SUPPLIED. No event-capture pipeline exists anywhere in this
codebase yet -- browser/audio/video interview-monitoring
infrastructure is unbuilt. These are placeholder inputs pending a
future browser/audio/video-tracking implementation, not events this
code detects itself.

Part of the integrity_ai module -- fully isolated from interview_ai/,
technical_ai/, screening_ai/, ats_engine/, scoring/, decision_ai/, and
visual_behavior_ai/. Only imports from integrity_ai.integrity_models
(intra-module, permitted). This module is deliberately NOT wired into
decision_ai/, visual_behavior_ai/, any summary generator, or any other
scoring system -- matching the "deliberately unwired, single day's
scope" precedent already established for visual_behavior_ai/ (Day 48)
and technical_ai/ (Days 46-47).

TWO DISTINCT CONSTANTS, TWO DISTINCT PURPOSES: EVENT_CAPS and
WARNING_THRESHOLDS are deliberately separate dictionaries. EVENT_CAPS
is the normalization denominator per signal -- the count at which a
signal's sub-score bottoms out at 0.0. WARNING_THRESHOLDS is the
single source of truth for warning triggers -- the count that must be
STRICTLY EXCEEDED before a warning string is emitted for that signal.
A warning threshold and a scoring-floor cap are two different
concepts and must not be conflated. Every function in this file that
checks a given signal's threshold reads from the SAME corresponding
constant (EVENT_CAPS for normalization, WARNING_THRESHOLDS for
warnings) -- no function may hardcode its own separate threshold
value for any signal. See integrity_ai/DAY49_DECISIONS.md.

DETERMINISM RULE (non-negotiable, project-wide): no use of the
`random` module anywhere in this file.
"""

from utils.logger import get_logger

from integrity_ai.integrity_models import (
    IntegrityEvents,
    IntegrityScore,
    IntegritySignals,
)

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Normalization caps
# ---------------------------------------------------------------------------

# The count at which a signal's sub-score bottoms out at 0.0 (maximum
# risk for that signal) -- i.e. the normalization denominator per
# signal. Distinct from WARNING_THRESHOLDS below; see module docstring.
EVENT_CAPS: dict[str, int] = {
    "tab_switch_count": 5,
    "focus_loss_count": 5,
    "external_voice_count": 3,
    "gaze_deviation_count": 5,
}

# Same order as IntegrityEvents field order.
REQUIRED_EVENT_KEYS: tuple[str, ...] = (
    "tab_switch_count",
    "focus_loss_count",
    "external_voice_count",
    "gaze_deviation_count",
)

# ---------------------------------------------------------------------------
# Weights
# ---------------------------------------------------------------------------

DEFAULT_WEIGHTS: dict[str, float] = {
    "tab_switch_signal": 0.25,
    "focus_loss_signal": 0.25,
    "external_voice_signal": 0.30,
    "gaze_deviation_signal": 0.20,
}
assert sum(DEFAULT_WEIGHTS.values()) == 1.0

# ---------------------------------------------------------------------------
# Warning thresholds
# ---------------------------------------------------------------------------

# Single source of truth for warning triggers -- deliberately SEPARATE
# from EVENT_CAPS, since a warning threshold and a scoring-floor cap
# are two different concepts. A raw count STRICTLY EXCEEDING the value
# here (not merely equalling it) triggers that signal's warning.
# Unlike the manager sample this project reviewed (where the
# tab-switch threshold disagreed across two functions, 3 vs 2), every
# function in this file that checks a given signal's threshold reads
# from this SAME constant -- no function may hardcode its own separate
# threshold value for any signal.
WARNING_THRESHOLDS: dict[str, int] = {
    "tab_switch_count": 3,
    "focus_loss_count": 3,
    "external_voice_count": 2,
    "gaze_deviation_count": 3,
}

# Maps each IntegrityEvents field name to its corresponding
# IntegritySignals field name, so the mapping between "count" keys and
# "signal" keys is defined exactly once.
_EVENT_TO_SIGNAL_KEY: dict[str, str] = {
    "tab_switch_count": "tab_switch_signal",
    "focus_loss_count": "focus_loss_signal",
    "external_voice_count": "external_voice_signal",
    "gaze_deviation_count": "gaze_deviation_signal",
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _normalize_signal(count: int, cap: int) -> float:
    """Normalize a raw event count into a [0.0, 1.0] "positive" signal.

    Formula: round(max(1.0 - (count / cap), 0.0), 4)

    A count of 0 yields 1.0 (no risk); a count >= cap yields 0.0
    (maximum risk for that signal).

    Args:
        count: Raw caller-supplied event count (>= 0).
        cap: Normalization denominator for this signal, from
            EVENT_CAPS.

    Returns:
        A float in [0.0, 1.0] rounded to 4 decimal places.
    """
    result = round(max(1.0 - (count / cap), 0.0), 4)
    logger.debug(
        "_normalize_signal(count=%r, cap=%r) -> %.4f", count, cap, result
    )
    return result


# ---------------------------------------------------------------------------
# Public scoring functions
# ---------------------------------------------------------------------------


def calculate_integrity_score(
    events: dict[str, int],
    weights: dict[str, float] = DEFAULT_WEIGHTS,
) -> IntegrityScore:
    """Score a set of caller-supplied integrity event counts.

    All four event counts in ``events`` are CALLER-SUPPLIED
    placeholders (see module docstring) -- this function performs no
    event capture of its own.

    DAY 49 VALIDATION PRECEDENT (mirrored from
    visual_behavior_ai.visual_behavior_scoring.calculate_visual_behavior_score,
    itself mirrored from
    technical_ai.technical_scoring_engine.technical_scoring_pipeline):
    required keys are explicitly validated as present and non-None
    BEFORE constructing the events model, so a missing key surfaces as
    a clear, diagnosable ValueError naming exactly which field(s) are
    missing, rather than a raw error deep inside Pydantic validation.
    Negative values are NOT manually checked here -- constructing
    ``IntegrityEvents`` naturally enforces that bound via its Field
    constraints, and that validation error is allowed to propagate
    unmodified.

    Args:
        events: Dict of caller-supplied raw event counts, keyed by the
            four names in REQUIRED_EVENT_KEYS.
        weights: Per-signal weights to apply, keyed by the four
            IntegritySignals field names. Defaults to DEFAULT_WEIGHTS.

    Returns:
        A fully populated IntegrityScore.

    Raises:
        ValueError: If any of REQUIRED_EVENT_KEYS is missing from or
            None in ``events``.
        pydantic.ValidationError: If any present event count is
            negative.
    """
    logger.debug("calculate_integrity_score called with events=%r", events)

    missing = [k for k in REQUIRED_EVENT_KEYS if events.get(k) is None]
    if missing:
        raise ValueError(
            f"calculate_integrity_score received an events dict "
            f"missing required field(s) {missing}: {events!r}. "
            f"tab_switch_count, focus_loss_count, external_voice_count, "
            f"and gaze_deviation_count must all be present and non-None."
        )

    events_model = IntegrityEvents(
        tab_switch_count=events["tab_switch_count"],
        focus_loss_count=events["focus_loss_count"],
        external_voice_count=events["external_voice_count"],
        gaze_deviation_count=events["gaze_deviation_count"],
    )

    signals_model = IntegritySignals(
        tab_switch_signal=_normalize_signal(
            events_model.tab_switch_count, EVENT_CAPS["tab_switch_count"]
        ),
        focus_loss_signal=_normalize_signal(
            events_model.focus_loss_count, EVENT_CAPS["focus_loss_count"]
        ),
        external_voice_signal=_normalize_signal(
            events_model.external_voice_count, EVENT_CAPS["external_voice_count"]
        ),
        gaze_deviation_signal=_normalize_signal(
            events_model.gaze_deviation_count, EVENT_CAPS["gaze_deviation_count"]
        ),
    )

    integrity_score = round(
        sum(
            getattr(signals_model, signal_key) * weights[signal_key]
            for signal_key in _EVENT_TO_SIGNAL_KEY.values()
        )
        * 100,
        2,
    )

    risk_level = get_integrity_risk_level(integrity_score)
    warnings = generate_integrity_warnings(events_model)

    logger.info(
        "calculate_integrity_score integrity_score=%.2f risk_level=%s warning_count=%d",
        integrity_score,
        risk_level,
        len(warnings),
    )

    return IntegrityScore(
        integrity_score=integrity_score,
        risk_level=risk_level,
        events=events_model,
        signals=signals_model,
        warnings=warnings,
    )


def get_integrity_risk_level(score: float) -> str:
    """Map an integrity score to a risk level label.

    POLARITY NOTE: HIGHER integrity_score means LOWER risk -- this is
    an inverted-scale label relative to score magnitude (a high score
    is good news), easy to get backwards. Same polarity convention as
    IntegritySignals, where higher = less risky.

    Args:
        score: Aggregate integrity score (0.0-100.0).

    Returns:
        "Low Risk" if score >= 75, "Moderate Risk" if score >= 50,
        otherwise "High Risk".
    """
    if score >= 75:
        return "Low Risk"
    if score >= 50:
        return "Moderate Risk"
    return "High Risk"


def generate_integrity_warnings(events: IntegrityEvents) -> list[str]:
    """Generate deterministic warning messages from raw event counts.

    Pure, deterministic function. For each of the four signals, if the
    raw count in ``events`` STRICTLY EXCEEDS the corresponding value
    in WARNING_THRESHOLDS, appends one fixed warning string to the
    returned list, in this fixed order: tab_switch, focus_loss,
    external_voice, gaze_deviation. This function reads
    WARNING_THRESHOLDS only -- it does not define or compare against
    any separate hardcoded number of its own.

    Args:
        events: Raw caller-supplied event counts.

    Returns:
        A list of warning strings (possibly empty, if no thresholds
        are exceeded).
    """
    warnings: list[str] = []

    if events.tab_switch_count > WARNING_THRESHOLDS["tab_switch_count"]:
        warnings.append("Frequent tab switching detected.")
    if events.focus_loss_count > WARNING_THRESHOLDS["focus_loss_count"]:
        warnings.append("Repeated loss of screen focus detected.")
    if events.external_voice_count > WARNING_THRESHOLDS["external_voice_count"]:
        warnings.append("Possible external voice detected.")
    if events.gaze_deviation_count > WARNING_THRESHOLDS["gaze_deviation_count"]:
        warnings.append("Frequent gaze deviation detected.")

    logger.debug(
        "generate_integrity_warnings -> %d warning(s): %r",
        len(warnings),
        warnings,
    )
    return warnings
