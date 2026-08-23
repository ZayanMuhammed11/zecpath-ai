"""
tests/test_final_decision_engine.py

pytest suite for the Day 52 Final Recommendation AI
(final_decision_ai/).
"""

import pytest

from final_decision_ai.final_decision_engine import (
    apply_risk_adjustment,
    build_visual_behavior_context,
    calculate_decision_confidence,
    final_decision_pipeline,
)
from final_decision_ai.final_decision_models import FinalDecision


# ---------------------------------------------------------------------------
# apply_risk_adjustment
# ---------------------------------------------------------------------------


def test_apply_risk_adjustment_none_input():
    result = apply_risk_adjustment(80.0, None)
    assert result.applied is False
    assert result.risk_level is None
    assert result.penalty_points == 0.0


def test_apply_risk_adjustment_low_risk():
    result = apply_risk_adjustment(80.0, "Low Risk")
    assert result.applied is True
    assert result.risk_level == "Low Risk"
    assert result.penalty_points == 0.0


def test_apply_risk_adjustment_moderate_risk():
    result = apply_risk_adjustment(80.0, "Moderate Risk")
    assert result.applied is True
    assert result.penalty_points == 7.0


def test_apply_risk_adjustment_high_risk():
    result = apply_risk_adjustment(80.0, "High Risk")
    assert result.applied is True
    assert result.penalty_points == 15.0


def test_apply_risk_adjustment_invalid_string_raises():
    with pytest.raises(ValueError):
        apply_risk_adjustment(80.0, "Extreme Risk")


# ---------------------------------------------------------------------------
# calculate_decision_confidence
# ---------------------------------------------------------------------------


def test_calculate_decision_confidence_empty_list():
    assert calculate_decision_confidence([]) == "high"


def test_calculate_decision_confidence_single_element():
    assert calculate_decision_confidence([80.0]) == "high"


def test_calculate_decision_confidence_small_variance():
    # variance = 85 - 80 = 5 <= 10 -> "high"
    assert calculate_decision_confidence([80.0, 85.0]) == "high"


def test_calculate_decision_confidence_medium_variance():
    # variance = 100 - 75 = 25 <= 30 -> "medium"
    assert calculate_decision_confidence([75.0, 100.0]) == "medium"


def test_calculate_decision_confidence_large_variance():
    # variance = 100 - 60 = 40 > 30 -> "low"
    assert calculate_decision_confidence([60.0, 100.0]) == "low"


# ---------------------------------------------------------------------------
# build_visual_behavior_context
# ---------------------------------------------------------------------------


def test_build_visual_behavior_context_both_none():
    assert build_visual_behavior_context(None, None) is None


def test_build_visual_behavior_context_values_supplied():
    context = build_visual_behavior_context(72.5, "Engaged")
    assert context is not None
    assert context.visual_behavior_score == 72.5
    assert context.level == "Engaged"
    assert context.note == (
        "Visual behavior data is informational only and does not "
        "affect the adjusted score or final recommendation."
    )


# ---------------------------------------------------------------------------
# final_decision_pipeline
# ---------------------------------------------------------------------------


def test_final_decision_pipeline_missing_final_score_raises():
    with pytest.raises(ValueError, match="final_score"):
        final_decision_pipeline(
            candidate_id="c1",
            unified_score={"recommendation": "selected"},
        )


def test_final_decision_pipeline_missing_recommendation_raises():
    with pytest.raises(ValueError, match="recommendation"):
        final_decision_pipeline(
            candidate_id="c1",
            unified_score={"final_score": 80.0},
        )


def test_final_decision_pipeline_no_integrity_data_no_adjustment():
    result = final_decision_pipeline(
        candidate_id="c1",
        unified_score={"final_score": 80.0, "recommendation": "selected"},
    )
    assert result.adjusted_score == 80.0
    assert result.risk_adjustment.applied is False


def test_final_decision_pipeline_high_risk_pushes_band_down():
    # base_score=80.0, High Risk penalty=15.0
    # adjusted_score = max(0.0, round(80.0 - 15.0, 2)) = 65.0
    # 65.0 >= 55 and < 75 -> "hold"
    result = final_decision_pipeline(
        candidate_id="c2",
        unified_score={"final_score": 80.0, "recommendation": "selected"},
        integrity_risk_level="High Risk",
    )
    assert result.adjusted_score == 65.0
    assert result.final_recommendation == "hold"
    assert result.base_recommendation == "selected"
    assert "changed the recommendation from 'selected' to 'hold'" in result.reasoning


def test_final_decision_pipeline_adjusted_score_floored_at_zero():
    # base_score=10.0, High Risk penalty=15.0
    # adjusted_score = max(0.0, round(10.0 - 15.0, 2)) = max(0.0, -5.0) = 0.0
    result = final_decision_pipeline(
        candidate_id="c3",
        unified_score={"final_score": 10.0, "recommendation": "rejected"},
        integrity_risk_level="High Risk",
    )
    assert result.adjusted_score == 0.0
    assert result.final_recommendation == "rejected"


def test_final_decision_pipeline_visual_behavior_passthrough_no_score_effect():
    result_a = final_decision_pipeline(
        candidate_id="c4",
        unified_score={"final_score": 60.0, "recommendation": "hold"},
        visual_behavior_score=20.0,
        visual_behavior_level="Disengaged",
    )
    result_b = final_decision_pipeline(
        candidate_id="c4",
        unified_score={"final_score": 60.0, "recommendation": "hold"},
        visual_behavior_score=95.0,
        visual_behavior_level="Highly Engaged",
    )

    assert result_a.visual_behavior_context.visual_behavior_score == 20.0
    assert result_b.visual_behavior_context.visual_behavior_score == 95.0
    # adjusted_score is identical regardless of visual_behavior_score
    assert result_a.adjusted_score == result_b.adjusted_score == 60.0
    assert result_a.final_recommendation == result_b.final_recommendation


def test_final_decision_pipeline_returns_final_decision_instance():
    result = final_decision_pipeline(
        candidate_id="c5",
        unified_score={"final_score": 50.0, "recommendation": "rejected"},
    )
    assert isinstance(result, FinalDecision)
