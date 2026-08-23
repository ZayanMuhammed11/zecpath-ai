"""Tests for decision_ai/unified_scoring_engine.py (Day 41, extended Day 51).

Day 51 rewrite: decision_ai now aggregates 5 rounds (ats, screening, hr,
technical, machine_test) instead of 3. See DAY51_DECISIONS.md for the
full list of which tests below were rewritten and why. In short: any
test whose expected numbers depended on the old 3-round ROLE_WEIGHTS
table, or whose RoundScores only populated the original 3 fields while
intending "all rounds present", required rewriting. Tests that were
already round-count-agnostic (boundary checks on a raw score, generic
loops over ROLE_WEIGHTS, single-round edge cases) needed no changes and
are kept exactly as they were.
"""

import pytest

from decision_ai.decision_models import RoleLevel, RoundScores, UnifiedScore
from decision_ai.round_weights import ROLE_WEIGHTS, get_weights, DEFAULT_WEIGHTS
from decision_ai.unified_scoring_engine import (
    calculate_hiring_fit,
    calculate_unified_score,
    generate_reasoning,
    get_confidence,
    get_recommendation,
    redistribute_weights,
    unified_scoring_pipeline,
)


def test_all_five_rounds_present_mid_role_exact_math():
    """1. REWRITTEN (was 3-round). All five rounds present, mid role_level
    — exact final_score math against the new 5-round weight table.

    mid weights: ats=0.20, screening=0.15, hr=0.25, technical=0.25,
    machine_test=0.15 (sums to 1.0, no redistribution needed).

    Hand computation:
        80*0.20 + 70*0.15 + 90*0.25 + 85*0.25 + 75*0.15
      = 16.0 + 10.5 + 22.5 + 21.25 + 11.25
      = 81.5
    """
    round_scores = RoundScores(
        ats_score=80,
        screening_score=70,
        hr_score=90,
        technical_score=85,
        machine_test_score=75,
    )
    base_weights = get_weights(RoleLevel.mid)
    weights = redistribute_weights(round_scores, base_weights)
    final_score, breakdown = calculate_unified_score(round_scores, weights)

    expected = round(80 * 0.20 + 70 * 0.15 + 90 * 0.25 + 85 * 0.25 + 75 * 0.15, 2)
    assert final_score == expected
    assert final_score == 81.5
    assert breakdown.rounds_included == [
        "ats", "screening", "hr", "technical", "machine_test",
    ]
    assert breakdown.rounds_missing == []


def test_missing_one_round_redistributes_and_scores_correctly():
    """2. REWRITTEN (was 3-round). Missing screening only (4 of 5 present)
    — redistributed weights sum to 1.0, score reflects the other four.

    Present mid weights: ats=0.20, hr=0.25, technical=0.25,
    machine_test=0.15 -> sum = 0.85.

    Hand computation:
        redistributed ats  = 0.20/0.85
        redistributed hr   = 0.25/0.85
        redistributed tech = 0.25/0.85
        redistributed mt   = 0.15/0.85
        final = (80*0.20 + 90*0.25 + 85*0.25 + 75*0.15) / 0.85
              = 71.0 / 0.85
              = 83.529411... -> rounds to 83.53
    """
    round_scores = RoundScores(
        ats_score=80,
        screening_score=None,
        hr_score=90,
        technical_score=85,
        machine_test_score=75,
    )
    base_weights = get_weights(RoleLevel.mid)
    weights = redistribute_weights(round_scores, base_weights)

    assert abs(sum(weights.values()) - 1.0) < 1e-6
    assert set(weights.keys()) == {"ats", "hr", "technical", "machine_test"}

    final_score, breakdown = calculate_unified_score(round_scores, weights)
    expected = round(
        (80 * 0.20 + 90 * 0.25 + 85 * 0.25 + 75 * 0.15) / 0.85, 2
    )
    assert final_score == expected
    assert final_score == 83.53
    assert breakdown.rounds_missing == ["screening"]


def test_only_one_round_present_full_weight_and_low_confidence():
    """3. UNCHANGED — re-verified, no rewrite needed. This test's intent
    ("exactly one round present") is unaffected by the 3->5 round
    expansion: with only hr populated (all other 4 fields at their None
    default), redistribute_weights still gives hr 100% of the weight
    regardless of how many total round slots exist, and get_confidence
    still maps present_count == 1 to "low" under the new proportional
    bands (1 -> low, same as before).
    """
    round_scores = RoundScores(ats_score=None, screening_score=None, hr_score=90)
    base_weights = get_weights(RoleLevel.mid)
    weights = redistribute_weights(round_scores, base_weights)

    assert weights == {"hr": 1.0}
    assert get_confidence(round_scores) == "low"

    final_score, _ = calculate_unified_score(round_scores, weights)
    assert final_score == 90.0


def test_all_rounds_none_raises_value_error():
    """4. UNCHANGED (renamed only, "three" -> "all", body untouched) —
    re-verified, no rewrite needed. RoundScores() with no arguments
    leaves all 5 fields at their None default, so redistribute_weights
    still has zero present_rounds and still raises the same ValueError
    with the same message, unaffected by the field-count change.
    """
    round_scores = RoundScores()
    base_weights = get_weights(RoleLevel.mid)

    with pytest.raises(ValueError, match="No round scores provided"):
        redistribute_weights(round_scores, base_weights)


def test_every_role_weight_set_sums_to_one():
    """5. UNCHANGED — re-verified, no rewrite needed. This loop is
    fully generic over whatever ROLE_WEIGHTS contains, so it
    automatically now verifies the new 5-round table (fresher, mid,
    senior each sum to 1.0). This also satisfies the Day 51 requirement
    to confirm every ROLE_WEIGHTS entry sums to 1.0 under the new
    5-round table — intentionally not duplicated as a separate test.
    """
    for role_level, weights in ROLE_WEIGHTS.items():
        assert abs(sum(weights.values()) - 1.0) < 1e-6, (
            f"{role_level} weights do not sum to 1.0"
        )


def test_get_weights_matches_each_defined_role_level():
    """6. UNCHANGED — re-verified, no rewrite needed. Generic equality
    check against ROLE_WEIGHTS plus copy-semantics check; unaffected by
    how many keys are inside each weight dict."""
    for role_level in RoleLevel:
        weights = get_weights(role_level)
        assert weights == ROLE_WEIGHTS[role_level]

    # returned dict must be a copy, not the underlying dict
    weights = get_weights(RoleLevel.mid)
    weights["ats"] = 999
    assert ROLE_WEIGHTS[RoleLevel.mid]["ats"] != 999
    assert DEFAULT_WEIGHTS["ats"] != 999


def test_recommendation_boundary_selected_at_75():
    """7. UNCHANGED — re-verified, no rewrite needed. get_recommendation
    operates on a plain float score and has no round-count dependency."""
    assert get_recommendation(75.0) == "selected"


def test_recommendation_boundary_rejected_and_hold():
    """8. UNCHANGED — re-verified, no rewrite needed. Same reasoning as
    test 7."""
    assert get_recommendation(54.99) == "rejected"
    assert get_recommendation(55.0) == "hold"


def test_hiring_fit_boundary_excellent_at_80():
    """9. UNCHANGED — re-verified, no rewrite needed. calculate_hiring_fit
    operates on a plain float score and has no round-count dependency."""
    fit = calculate_hiring_fit(80.0)
    assert fit.fit_category == "Excellent Fit"
    assert fit.hiring_fit_percentage == 80.0


def test_get_confidence_maps_proportion_of_five_to_level():
    """10. REWRITTEN (was 3-round raw-count test). get_confidence now
    uses proportion-of-5 bands:
        5 or 4 rounds present -> "high"
        3 or 2 rounds present -> "medium"
        1 round present       -> "low"
    Covers all five present-counts (5, 4, 3, 2, 1) mapped to their
    correct band, replacing the old count-out-of-3-only test.
    """
    five = RoundScores(
        ats_score=50, screening_score=50, hr_score=50,
        technical_score=50, machine_test_score=50,
    )
    four = RoundScores(
        ats_score=50, screening_score=50, hr_score=50,
        technical_score=50, machine_test_score=None,
    )
    three = RoundScores(
        ats_score=50, screening_score=50, hr_score=50,
        technical_score=None, machine_test_score=None,
    )
    two = RoundScores(
        ats_score=50, screening_score=50, hr_score=None,
        technical_score=None, machine_test_score=None,
    )
    one = RoundScores(
        ats_score=None, screening_score=None, hr_score=50,
        technical_score=None, machine_test_score=None,
    )

    assert get_confidence(five) == "high"
    assert get_confidence(four) == "high"
    assert get_confidence(three) == "medium"
    assert get_confidence(two) == "medium"
    assert get_confidence(one) == "low"


def test_generate_reasoning_reflects_real_computed_data():
    """11. REWRITTEN (was 3-round). Same round_scores/weights as test 1
    (all five rounds present, mid role) so this exercises reasoning
    generation against real 5-round breakdown data. hr remains the top
    contributor (22.5 out of 81.5 total), so "hr" is still expected to
    appear in the reasoning text, and the "selected" recommendation
    (81.5 >= 75) is expected to appear too.
    """
    round_scores = RoundScores(
        ats_score=80,
        screening_score=70,
        hr_score=90,
        technical_score=85,
        machine_test_score=75,
    )
    base_weights = get_weights(RoleLevel.mid)
    weights = redistribute_weights(round_scores, base_weights)
    final_score, breakdown = calculate_unified_score(round_scores, weights)
    recommendation = get_recommendation(final_score)

    assert recommendation == "selected"

    reasoning = generate_reasoning(breakdown, recommendation)

    assert "hr" in reasoning
    assert recommendation in reasoning
    # the top contributor's weighted_contribution value should appear formatted
    top_contribution = max(
        breakdown.contributions, key=lambda c: c.weighted_contribution
    )
    assert f"{top_contribution.weighted_contribution:.2f}" in reasoning


def test_generate_reasoning_mentions_missing_rounds():
    """REWRITTEN — was previously a 3-round "missing screening" case
    where ats/hr were the only other rounds. Under the 5-round model,
    supplying only ats/hr would ALSO leave technical and machine_test
    missing, changing the test's intent. Rewritten to use the same
    4-of-5 setup as test 2 (only screening missing) so the reasoning
    text's "missing rounds" callout is isolated to screening alone.
    """
    round_scores = RoundScores(
        ats_score=80,
        screening_score=None,
        hr_score=90,
        technical_score=85,
        machine_test_score=75,
    )
    base_weights = get_weights(RoleLevel.mid)
    weights = redistribute_weights(round_scores, base_weights)
    final_score, breakdown = calculate_unified_score(round_scores, weights)
    recommendation = get_recommendation(final_score)

    reasoning = generate_reasoning(breakdown, recommendation)

    assert "screening" in reasoning
    assert "redistributed" in reasoning


def test_unified_scoring_pipeline_full_integration():
    """12. REWRITTEN (was 3-round). unified_scoring_pipeline() full
    integration for a realistic 5-round input, senior role_level.

    senior weights: ats=0.20, screening=0.10, hr=0.25, technical=0.30,
    machine_test=0.15.

    Hand computation:
        85*0.20 + 78*0.10 + 92*0.25 + 88*0.30 + 80*0.15
      = 17.0 + 7.8 + 23.0 + 26.4 + 12.0
      = 86.2
    """
    round_scores = RoundScores(
        ats_score=85,
        screening_score=78,
        hr_score=92,
        technical_score=88,
        machine_test_score=80,
    )
    result = unified_scoring_pipeline(
        candidate_id="cand-123",
        round_scores=round_scores,
        role_level=RoleLevel.senior,
    )

    assert isinstance(result, UnifiedScore)
    assert result.candidate_id == "cand-123"
    assert result.role_level_used == RoleLevel.senior

    expected_weights = ROLE_WEIGHTS[RoleLevel.senior]
    expected_final = round(
        85 * expected_weights["ats"]
        + 78 * expected_weights["screening"]
        + 92 * expected_weights["hr"]
        + 88 * expected_weights["technical"]
        + 80 * expected_weights["machine_test"],
        2,
    )
    assert result.final_score == expected_final
    assert result.final_score == 86.2
    assert result.recommendation in {"selected", "hold", "rejected"}
    assert result.confidence == "high"
    assert result.breakdown.rounds_included == [
        "ats", "screening", "hr", "technical", "machine_test",
    ]
    assert result.breakdown.rounds_missing == []
    assert result.hiring_fit.hiring_fit_percentage == result.final_score
    assert result.reasoning != ""


def test_unified_scoring_pipeline_raises_for_no_rounds():
    """13. UNCHANGED — re-verified, no rewrite needed. Integration: an
    all-missing RoundScores() still raises through the full pipeline,
    unaffected by the field-count change (same reasoning as test 4)."""
    round_scores = RoundScores()
    with pytest.raises(ValueError, match="No round scores provided"):
        unified_scoring_pipeline(candidate_id="cand-empty", round_scores=round_scores)


# ---------------------------------------------------------------------------
# New tests (Day 51): 5-round scenarios that were not previously testable
# under the 3-round model.
# ---------------------------------------------------------------------------


def test_all_five_rounds_present_fresher_role_exact_math():
    """NEW 1. All five rounds present, fresher role_level (distinct from
    the mid-role case in test 1) — exact hand-computed final_score, plus
    confidence == "high".

    fresher weights: ats=0.15, screening=0.20, hr=0.25, technical=0.20,
    machine_test=0.20.

    Hand computation:
        60*0.15 + 70*0.20 + 80*0.25 + 90*0.20 + 50*0.20
      = 9.0 + 14.0 + 20.0 + 18.0 + 10.0
      = 71.0
    """
    round_scores = RoundScores(
        ats_score=60,
        screening_score=70,
        hr_score=80,
        technical_score=90,
        machine_test_score=50,
    )
    base_weights = get_weights(RoleLevel.fresher)
    weights = redistribute_weights(round_scores, base_weights)
    final_score, breakdown = calculate_unified_score(round_scores, weights)

    expected = round(60 * 0.15 + 70 * 0.20 + 80 * 0.25 + 90 * 0.20 + 50 * 0.20, 2)
    assert final_score == expected
    assert final_score == 71.0
    assert breakdown.rounds_missing == []
    assert get_confidence(round_scores) == "high"


def test_exactly_two_of_five_rounds_present_confidence_medium():
    """NEW 2. Exactly 2 of 5 rounds present (ats and technical) —
    confidence == "medium", and redistributed weights are hand-verified
    to sum to 1.0.

    mid weights for the present rounds: ats=0.20, technical=0.25 -> sum
    = 0.45.
        redistributed ats        = 0.20/0.45 = 0.444444...
        redistributed technical  = 0.25/0.45 = 0.555555...
    """
    round_scores = RoundScores(
        ats_score=72,
        screening_score=None,
        hr_score=None,
        technical_score=88,
        machine_test_score=None,
    )
    base_weights = get_weights(RoleLevel.mid)
    weights = redistribute_weights(round_scores, base_weights)

    assert set(weights.keys()) == {"ats", "technical"}
    assert abs(weights["ats"] - (0.20 / 0.45)) < 1e-9
    assert abs(weights["technical"] - (0.25 / 0.45)) < 1e-9
    assert abs(sum(weights.values()) - 1.0) < 1e-6

    assert get_confidence(round_scores) == "medium"


def test_exactly_three_of_five_rounds_present_confidence_medium():
    """NEW 3. Exactly 3 of 5 rounds present (ats, hr, technical) —
    confidence == "medium" (distinct from the 2-of-5 case above), and
    redistributed weights hand-verified to sum to 1.0.

    mid weights for the present rounds: ats=0.20, hr=0.25,
    technical=0.25 -> sum = 0.70.
        redistributed ats        = 0.20/0.70 = 0.285714...
        redistributed hr         = 0.25/0.70 = 0.357142...
        redistributed technical  = 0.25/0.70 = 0.357142...
    """
    round_scores = RoundScores(
        ats_score=65,
        screening_score=None,
        hr_score=77,
        technical_score=83,
        machine_test_score=None,
    )
    base_weights = get_weights(RoleLevel.mid)
    weights = redistribute_weights(round_scores, base_weights)

    assert set(weights.keys()) == {"ats", "hr", "technical"}
    assert abs(weights["ats"] - (0.20 / 0.70)) < 1e-9
    assert abs(weights["hr"] - (0.25 / 0.70)) < 1e-9
    assert abs(weights["technical"] - (0.25 / 0.70)) < 1e-9
    assert abs(sum(weights.values()) - 1.0) < 1e-6

    assert get_confidence(round_scores) == "medium"


def test_pipeline_includes_machine_test_score_contribution():
    """NEW 4. Full pipeline run including a machine_test_score, confirming
    it is genuinely included in breakdown.rounds_included and
    contributes to final_score — i.e. is not silently ignored.

    Verified two ways: (a) "machine_test" appears in rounds_included and
    has a RoundContribution with a nonzero weighted_contribution, and
    (b) changing machine_test_score changes the resulting final_score,
    proving it actually feeds into the weighted sum rather than being
    dropped.
    """
    base_scores = dict(
        ats_score=70, screening_score=70, hr_score=70, technical_score=70,
    )
    with_low_mt = RoundScores(**base_scores, machine_test_score=40)
    with_high_mt = RoundScores(**base_scores, machine_test_score=95)

    result_low = unified_scoring_pipeline(
        candidate_id="cand-mt-low", round_scores=with_low_mt, role_level=RoleLevel.mid,
    )
    result_high = unified_scoring_pipeline(
        candidate_id="cand-mt-high", round_scores=with_high_mt, role_level=RoleLevel.mid,
    )

    assert "machine_test" in result_low.breakdown.rounds_included
    assert "machine_test" in result_high.breakdown.rounds_included

    mt_contribution_low = next(
        c for c in result_low.breakdown.contributions if c.round_name == "machine_test"
    )
    assert mt_contribution_low.raw_score == 40
    assert mt_contribution_low.weighted_contribution > 0

    # Changing only machine_test_score must change the final_score —
    # proving it is not silently ignored in the weighted sum.
    assert result_low.final_score != result_high.final_score
