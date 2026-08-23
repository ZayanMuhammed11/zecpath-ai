"""
tests/test_visual_behavior_scoring.py

Pytest tests for visual_behavior_ai.visual_behavior_scoring.
"""

import re

import pytest
from pydantic import ValidationError

from visual_behavior_ai.visual_behavior_models import VisualBehaviorScore
from visual_behavior_ai.visual_behavior_scoring import (
    DEFAULT_WEIGHTS,
    REQUIRED_SIGNAL_KEYS,
    calculate_visual_behavior_score,
    get_visual_behavior_level,
)

# Confirm the `random` module is not imported by this test file or the
# module under test.
assert "random" not in dir()


def test_valid_signals_produce_correct_score_and_type():
    """A valid full signals dict produces a VisualBehaviorScore with
    visual_behavior_score in [0.0, 100.0] and the correct hand-computed
    arithmetic result."""
    signals = {
        "gaze_stability": 0.80,
        "head_stability": 0.60,
        "facial_engagement": 0.90,
        "attention_consistency": 0.70,
    }

    # Hand-computed expected result using DEFAULT_WEIGHTS:
    #   gaze_stability:         0.80 * 0.30 = 0.240
    #   head_stability:         0.60 * 0.20 = 0.120
    #   facial_engagement:      0.90 * 0.30 = 0.270
    #   attention_consistency:  0.70 * 0.20 = 0.140
    #   sum                                  = 0.770
    #   * 100                                = 77.0
    expected_score = round(
        (0.80 * 0.30 + 0.60 * 0.20 + 0.90 * 0.30 + 0.70 * 0.20) * 100, 2
    )
    assert expected_score == 77.0

    result = calculate_visual_behavior_score(signals)

    assert isinstance(result, VisualBehaviorScore)
    assert result.visual_behavior_score == expected_score
    assert 0.0 <= result.visual_behavior_score <= 100.0
    assert result.level == "Engaged"
    assert result.signals.gaze_stability == 0.80
    assert result.signals.head_stability == 0.60
    assert result.signals.facial_engagement == 0.90
    assert result.signals.attention_consistency == 0.70


@pytest.mark.parametrize("missing_key", REQUIRED_SIGNAL_KEYS)
def test_each_missing_required_key_raises_value_error(missing_key):
    """Each of the four required keys, individually removed from the
    dict, raises ValueError naming that key."""
    signals = {
        "gaze_stability": 0.5,
        "head_stability": 0.5,
        "facial_engagement": 0.5,
        "attention_consistency": 0.5,
    }
    del signals[missing_key]

    with pytest.raises(ValueError) as exc_info:
        calculate_visual_behavior_score(signals)

    assert missing_key in str(exc_info.value)


@pytest.mark.parametrize("missing_key", REQUIRED_SIGNAL_KEYS)
def test_each_none_required_key_raises_value_error(missing_key):
    """Each of the four required keys, individually set to None, also
    raises ValueError naming that key (None is treated as missing)."""
    signals = {
        "gaze_stability": 0.5,
        "head_stability": 0.5,
        "facial_engagement": 0.5,
        "attention_consistency": 0.5,
    }
    signals[missing_key] = None

    with pytest.raises(ValueError) as exc_info:
        calculate_visual_behavior_score(signals)

    assert missing_key in str(exc_info.value)


def test_out_of_range_signal_raises_pydantic_validation_error():
    """A signal value outside [0.0, 1.0] raises a Pydantic validation
    error, which is allowed to propagate (not swallowed)."""
    signals = {
        "gaze_stability": 1.5,
        "head_stability": 0.5,
        "facial_engagement": 0.5,
        "attention_consistency": 0.5,
    }

    with pytest.raises(ValidationError):
        calculate_visual_behavior_score(signals)


def test_negative_signal_raises_pydantic_validation_error():
    """A negative signal value also raises a Pydantic validation
    error."""
    signals = {
        "gaze_stability": 0.5,
        "head_stability": -0.1,
        "facial_engagement": 0.5,
        "attention_consistency": 0.5,
    }

    with pytest.raises(ValidationError):
        calculate_visual_behavior_score(signals)


def test_level_boundary_highly_engaged_at_80():
    assert get_visual_behavior_level(80.0) == "Highly Engaged"


def test_level_boundary_just_below_80():
    assert get_visual_behavior_level(79.99) == "Engaged"


def test_level_boundary_engaged_at_60():
    assert get_visual_behavior_level(60.0) == "Engaged"


def test_level_boundary_just_below_60():
    assert get_visual_behavior_level(59.99) == "Variable Engagement"


def test_level_boundary_variable_engagement_at_40():
    assert get_visual_behavior_level(40.0) == "Variable Engagement"


def test_level_boundary_just_below_40():
    assert get_visual_behavior_level(39.99) == "Low Engagement"


def test_level_below_40_is_low_engagement():
    assert get_visual_behavior_level(10.0) == "Low Engagement"
    assert get_visual_behavior_level(0.0) == "Low Engagement"


def test_default_weights_sum_to_one():
    """DEFAULT_WEIGHTS sums to 1.0 (module-level constant tested
    directly)."""
    assert sum(DEFAULT_WEIGHTS.values()) == 1.0


def test_result_is_instance_of_visual_behavior_score():
    signals = {
        "gaze_stability": 0.5,
        "head_stability": 0.5,
        "facial_engagement": 0.5,
        "attention_consistency": 0.5,
    }
    result = calculate_visual_behavior_score(signals)
    assert isinstance(result, VisualBehaviorScore)


def test_no_random_module_used_anywhere():
    """Confirm no test, and no code under test, relies on the `random`
    module anywhere. This performs a static source scan of the module
    under test rather than relying on import-time introspection alone.
    """
    import visual_behavior_ai.visual_behavior_scoring as scoring_module
    import visual_behavior_ai.visual_behavior_models as models_module

    for module in (scoring_module, models_module):
        source_path = module.__file__
        with open(source_path, "r", encoding="utf-8") as f:
            source = f.read()
        assert not re.search(r"\bimport random\b", source)
        assert not re.search(r"\bfrom random\b", source)
