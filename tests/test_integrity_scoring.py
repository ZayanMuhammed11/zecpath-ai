"""
tests/test_integrity_scoring.py

Real pytest tests for integrity_ai.integrity_scoring /
integrity_ai.integrity_models (Day 49).
"""

import pytest
from pydantic import ValidationError

from integrity_ai.integrity_models import IntegrityEvents, IntegrityScore
from integrity_ai.integrity_scoring import (
    DEFAULT_WEIGHTS,
    EVENT_CAPS,
    REQUIRED_EVENT_KEYS,
    WARNING_THRESHOLDS,
    calculate_integrity_score,
    generate_integrity_warnings,
    get_integrity_risk_level,
)


# ---------------------------------------------------------------------------
# calculate_integrity_score: happy path
# ---------------------------------------------------------------------------


def test_calculate_integrity_score_valid_events_hand_computed():
    """A valid full events dict produces an IntegrityScore with
    integrity_score in [0.0, 100.0] and matches a hand-computed
    expected value.
    """
    events = {
        "tab_switch_count": 1,
        "focus_loss_count": 2,
        "external_voice_count": 0,
        "gaze_deviation_count": 3,
    }

    # Hand computation, mirroring _normalize_signal:
    #   round(max(1.0 - count/cap, 0.0), 4)
    #
    # tab_switch_signal   = round(max(1.0 - 1/5, 0.0), 4) = 0.8
    # focus_loss_signal   = round(max(1.0 - 2/5, 0.0), 4) = 0.6
    # external_voice_sig  = round(max(1.0 - 0/3, 0.0), 4) = 1.0
    # gaze_deviation_sig  = round(max(1.0 - 3/5, 0.0), 4) = 0.4
    #
    # weights: tab_switch=0.25, focus_loss=0.25, external_voice=0.30,
    #          gaze_deviation=0.20
    #
    # weighted sum = 0.8*0.25 + 0.6*0.25 + 1.0*0.30 + 0.4*0.20
    #              = 0.2 + 0.15 + 0.3 + 0.08
    #              = 0.73
    # integrity_score = round(0.73 * 100, 2) = 73.0
    expected_score = round(
        (
            0.8 * DEFAULT_WEIGHTS["tab_switch_signal"]
            + 0.6 * DEFAULT_WEIGHTS["focus_loss_signal"]
            + 1.0 * DEFAULT_WEIGHTS["external_voice_signal"]
            + 0.4 * DEFAULT_WEIGHTS["gaze_deviation_signal"]
        )
        * 100,
        2,
    )
    assert expected_score == 73.0

    result = calculate_integrity_score(events)

    assert isinstance(result, IntegrityScore)
    assert 0.0 <= result.integrity_score <= 100.0
    assert result.integrity_score == expected_score
    assert result.risk_level == get_integrity_risk_level(expected_score)


# ---------------------------------------------------------------------------
# calculate_integrity_score: missing / None required keys
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("missing_key", REQUIRED_EVENT_KEYS)
def test_calculate_integrity_score_missing_key_raises_value_error(missing_key):
    """Each of the four required keys, individually removed from the
    dict, raises ValueError naming that key.
    """
    events = {
        "tab_switch_count": 1,
        "focus_loss_count": 1,
        "external_voice_count": 1,
        "gaze_deviation_count": 1,
    }
    del events[missing_key]

    with pytest.raises(ValueError) as exc_info:
        calculate_integrity_score(events)

    assert missing_key in str(exc_info.value)


@pytest.mark.parametrize("none_key", REQUIRED_EVENT_KEYS)
def test_calculate_integrity_score_none_key_raises_value_error(none_key):
    """Each of the four required keys, individually set to None,
    raises ValueError naming that key.
    """
    events = {
        "tab_switch_count": 1,
        "focus_loss_count": 1,
        "external_voice_count": 1,
        "gaze_deviation_count": 1,
    }
    events[none_key] = None

    with pytest.raises(ValueError) as exc_info:
        calculate_integrity_score(events)

    assert none_key in str(exc_info.value)


# ---------------------------------------------------------------------------
# Negative event counts propagate Pydantic's own validation error
# ---------------------------------------------------------------------------


def test_negative_event_count_raises_pydantic_validation_error():
    """A negative event count raises a Pydantic validation error,
    propagated unmodified (not caught/wrapped).
    """
    events = {
        "tab_switch_count": -1,
        "focus_loss_count": 1,
        "external_voice_count": 1,
        "gaze_deviation_count": 1,
    }
    with pytest.raises(ValidationError):
        calculate_integrity_score(events)


def test_negative_event_count_raises_pydantic_validation_error_direct_model():
    """Directly constructing IntegrityEvents with a negative count
    also raises ValidationError (sanity check on the model itself).
    """
    with pytest.raises(ValidationError):
        IntegrityEvents(
            tab_switch_count=1,
            focus_loss_count=-5,
            external_voice_count=1,
            gaze_deviation_count=1,
        )


# ---------------------------------------------------------------------------
# get_integrity_risk_level: explicit band boundaries
# ---------------------------------------------------------------------------


def test_risk_level_low_risk_boundary_at_75():
    assert get_integrity_risk_level(75.0) == "Low Risk"


def test_risk_level_just_below_75_is_moderate():
    assert get_integrity_risk_level(74.99) == "Moderate Risk"


def test_risk_level_moderate_risk_boundary_at_50():
    assert get_integrity_risk_level(50.0) == "Moderate Risk"


def test_risk_level_just_below_50_is_high():
    assert get_integrity_risk_level(49.99) == "High Risk"


def test_risk_level_well_below_50_is_high():
    assert get_integrity_risk_level(10.0) == "High Risk"


# ---------------------------------------------------------------------------
# generate_integrity_warnings
# ---------------------------------------------------------------------------


def test_generate_integrity_warnings_zero_warnings():
    """No thresholds exceeded -> empty list."""
    events = IntegrityEvents(
        tab_switch_count=WARNING_THRESHOLDS["tab_switch_count"],
        focus_loss_count=WARNING_THRESHOLDS["focus_loss_count"],
        external_voice_count=WARNING_THRESHOLDS["external_voice_count"],
        gaze_deviation_count=WARNING_THRESHOLDS["gaze_deviation_count"],
    )
    warnings = generate_integrity_warnings(events)
    assert warnings == []


def test_generate_integrity_warnings_exactly_one_warning():
    """Exactly one threshold strictly exceeded -> exactly one warning,
    with the exact expected string.
    """
    events = IntegrityEvents(
        tab_switch_count=WARNING_THRESHOLDS["tab_switch_count"] + 1,
        focus_loss_count=WARNING_THRESHOLDS["focus_loss_count"],
        external_voice_count=WARNING_THRESHOLDS["external_voice_count"],
        gaze_deviation_count=WARNING_THRESHOLDS["gaze_deviation_count"],
    )
    warnings = generate_integrity_warnings(events)
    assert warnings == ["Frequent tab switching detected."]


def test_generate_integrity_warnings_all_four_warnings_in_order():
    """All four thresholds strictly exceeded -> all four warnings, in
    the fixed order: tab_switch, focus_loss, external_voice,
    gaze_deviation.
    """
    events = IntegrityEvents(
        tab_switch_count=WARNING_THRESHOLDS["tab_switch_count"] + 1,
        focus_loss_count=WARNING_THRESHOLDS["focus_loss_count"] + 1,
        external_voice_count=WARNING_THRESHOLDS["external_voice_count"] + 1,
        gaze_deviation_count=WARNING_THRESHOLDS["gaze_deviation_count"] + 1,
    )
    warnings = generate_integrity_warnings(events)
    assert len(warnings) == 4
    assert warnings == [
        "Frequent tab switching detected.",
        "Repeated loss of screen focus detected.",
        "Possible external voice detected.",
        "Frequent gaze deviation detected.",
    ]


# ---------------------------------------------------------------------------
# Constants sanity checks
# ---------------------------------------------------------------------------


def test_warning_thresholds_and_event_caps_are_distinct_and_meaningful():
    """WARNING_THRESHOLDS and EVENT_CAPS are distinct dictionaries with
    independently meaningful values, not simply aliased to each other.
    """
    assert WARNING_THRESHOLDS is not EVENT_CAPS
    assert WARNING_THRESHOLDS != EVENT_CAPS
    # Both must actually be used: keys match the same four signals,
    # but at least one value must differ per signal to prove they are
    # genuinely independent constants.
    assert set(WARNING_THRESHOLDS.keys()) == set(EVENT_CAPS.keys())
    assert any(
        WARNING_THRESHOLDS[key] != EVENT_CAPS[key] for key in WARNING_THRESHOLDS
    )


def test_default_weights_sum_to_one():
    assert sum(DEFAULT_WEIGHTS.values()) == 1.0


def test_calculate_integrity_score_returns_integrity_score_instance():
    events = {
        "tab_switch_count": 0,
        "focus_loss_count": 0,
        "external_voice_count": 0,
        "gaze_deviation_count": 0,
    }
    result = calculate_integrity_score(events)
    assert isinstance(result, IntegrityScore)
    assert result.integrity_score == 100.0
    assert result.risk_level == "Low Risk"
    assert result.warnings == []


# ---------------------------------------------------------------------------
# Determinism: no test in this file relies on the `random` module
# ---------------------------------------------------------------------------


def test_no_random_module_used_in_this_test_file():
    """Confirm no test in this module relies on the `random` module."""
    import sys

    this_module = sys.modules[__name__]
    assert not hasattr(this_module, "random")
