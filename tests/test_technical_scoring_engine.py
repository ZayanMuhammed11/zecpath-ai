"""
tests/test_technical_scoring_engine.py

Tests for technical_ai/technical_scoring_engine.py.
"""

import pytest

from technical_ai.technical_scoring_engine import (
    aggregate_technical_scores,
    get_skill_breakdown,
    get_technical_decision,
    score_depth,
    score_logic,
    score_real_world,
    score_technical_answer,
    technical_scoring_pipeline,
)
from technical_ai.technical_scoring_models import TechnicalAnswerScore


# ---------------------------------------------------------------------------
# score_depth
# ---------------------------------------------------------------------------


def test_score_depth_zero_markers():
    assert score_depth("This answer has nothing relevant in it at all.") == 0.0


def test_score_depth_multi_marker():
    text = "The root cause was a tolerance deviation that created risk."
    # distinct markers found: "root cause", "tolerance", "deviation", "risk" -> 4
    result = score_depth(text)
    assert result == 1.0


# ---------------------------------------------------------------------------
# score_logic
# ---------------------------------------------------------------------------


def test_score_logic_zero_markers():
    assert score_logic("No sequencing words present here whatsoever.") == 0.0


def test_score_logic_multi_marker():
    text = "First we checked the gauge, then therefore we escalated it."
    # distinct markers: "first", "then", "therefore" -> 3 / 4
    result = score_logic(text)
    assert result == round(3 / 4, 4)


# ---------------------------------------------------------------------------
# score_real_world
# ---------------------------------------------------------------------------


def test_score_real_world_zero_markers():
    assert score_real_world("Nothing applicable mentioned in this text.") == 0.0


def test_score_real_world_multi_marker_no_floor():
    text = (
        "In practice, on the production line, for example during an "
        "audit we caught the deviation early."
    )
    # distinct markers: "in practice", "on the production line",
    # "for example", "during an audit" -> capped at denominator 3 -> 1.0
    result = score_real_world(text)
    assert result == 1.0


def test_score_real_world_length_floor_triggers():
    text = "For example"  # 2 words, 1 marker matched
    result = score_real_world(text)
    # would be 1/3 = 0.3333 uncapped, well under 0.5, so floor isn't
    # actually the binding constraint here -- use a case where the
    # ratio alone would exceed 0.5 but word_count < 6.
    assert result <= 0.5

    text_short_high_ratio = "for example in the field"  # 5 words, 2 markers
    result2 = score_real_world(text_short_high_ratio)
    # 2/3 = 0.6667 uncapped, word_count=5 < 6 -> capped at 0.5
    assert result2 == 0.5


# ---------------------------------------------------------------------------
# score_technical_answer
# ---------------------------------------------------------------------------


def test_score_technical_answer_empty_text_zero_breakdown_respects_accuracy():
    result = score_technical_answer(
        question_id="TQ_AUTO_EXP_001",
        skill_domain="automotive_quality",
        accuracy=0.8,
        text="",
    )
    assert result.breakdown.accuracy == 0.8
    assert result.breakdown.depth == 0.0
    assert result.breakdown.logic == 0.0
    assert result.breakdown.real_world == 0.0
    # final_score = 0.8 * 0.40 * 100 = 32.0
    assert result.final_score == 32.0


def test_score_technical_answer_whitespace_only_text_zero_breakdown():
    result = score_technical_answer(
        question_id="TQ_FOOD_CONC_002",
        skill_domain="food_safety_systems",
        accuracy=0.0,
        text="   ",
    )
    assert result.breakdown.depth == 0.0
    assert result.breakdown.logic == 0.0
    assert result.breakdown.real_world == 0.0
    assert result.final_score == 0.0


def test_score_technical_answer_nonempty_text_invokes_subscorers():
    text = (
        "First, we identified the root cause, therefore we adjusted the "
        "tolerance. In practice this reduced risk on the production line."
    )
    result = score_technical_answer(
        question_id="TQ_PHARMA_SCEN_001",
        skill_domain="pharmaceutical_quality",
        accuracy=1.0,
        text=text,
    )
    assert result.breakdown.depth > 0.0
    assert result.breakdown.logic > 0.0
    assert result.breakdown.real_world > 0.0


# ---------------------------------------------------------------------------
# aggregate_technical_scores
# ---------------------------------------------------------------------------


def test_aggregate_technical_scores_mean_not_sum():
    answers = [
        TechnicalAnswerScore(
            question_id=f"Q{i}",
            skill_domain="automotive_quality",
            final_score=score,
            breakdown={
                "accuracy": 1.0,
                "depth": 1.0,
                "logic": 1.0,
                "real_world": 1.0,
            },
        )
        for i, score in enumerate([60.0, 80.0, 100.0])
    ]
    assert aggregate_technical_scores(answers) == 80.0


def test_aggregate_technical_scores_empty_list():
    assert aggregate_technical_scores([]) == 0.0


# ---------------------------------------------------------------------------
# get_skill_breakdown
# ---------------------------------------------------------------------------


def test_get_skill_breakdown_omits_empty_domains():
    answers = [
        TechnicalAnswerScore(
            question_id="Q1",
            skill_domain="automotive_quality",
            final_score=70.0,
            breakdown={
                "accuracy": 1.0,
                "depth": 1.0,
                "logic": 1.0,
                "real_world": 1.0,
            },
        ),
        TechnicalAnswerScore(
            question_id="Q2",
            skill_domain="automotive_quality",
            final_score=90.0,
            breakdown={
                "accuracy": 1.0,
                "depth": 1.0,
                "logic": 1.0,
                "real_world": 1.0,
            },
        ),
    ]
    breakdown = get_skill_breakdown(answers)
    assert breakdown == {"automotive_quality": 80.0}
    assert "food_safety_systems" not in breakdown
    assert "pharmaceutical_quality" not in breakdown


# ---------------------------------------------------------------------------
# get_technical_decision
# ---------------------------------------------------------------------------


def test_get_technical_decision_boundaries_75():
    assert get_technical_decision(74.99) == "Moderate Technical Fit"
    assert get_technical_decision(75.0) == "Strong Technical Fit"


def test_get_technical_decision_boundaries_55():
    assert get_technical_decision(54.99) == "Weak Technical Fit"
    assert get_technical_decision(55.0) == "Moderate Technical Fit"


# ---------------------------------------------------------------------------
# technical_scoring_pipeline
# ---------------------------------------------------------------------------


def test_pipeline_missing_key_raises_value_error_naming_field():
    answers = [
        {
            "question_id": "TQ_AUTO_EXP_001",
            "skill_domain": "automotive_quality",
            "phase": "experience_based",
            "accuracy": 0.9,
            # "text" intentionally omitted -> None via .get()
        }
    ]
    with pytest.raises(ValueError) as exc_info:
        technical_scoring_pipeline(answers)
    assert "text" in str(exc_info.value)


def test_pipeline_filters_out_introduction_phase_keeps_conceptual():
    answers = [
        {
            "question_id": "TQ_AUTO_INTRO_001",
            "skill_domain": "automotive_quality",
            "phase": "introduction",
            "accuracy": 1.0,
            "text": "Nice to meet you.",
        },
        {
            "question_id": "TQ_AUTO_CONC_001",
            "skill_domain": "automotive_quality",
            "phase": "conceptual",
            "accuracy": 1.0,
            "text": "First we analyzed the root cause, therefore risk dropped.",
        },
    ]
    result = technical_scoring_pipeline(answers)
    ids = [a.question_id for a in result.scored_answers]
    assert "TQ_AUTO_INTRO_001" not in ids
    assert "TQ_AUTO_CONC_001" in ids
    assert len(result.scored_answers) == 1


def test_pipeline_all_filtered_returns_zero_state():
    answers = [
        {
            "question_id": "TQ_AUTO_INTRO_001",
            "skill_domain": "automotive_quality",
            "phase": "introduction",
            "accuracy": 1.0,
            "text": "Hello.",
        },
        {
            "question_id": "TQ_AUTO_CLOSE_001",
            "skill_domain": "automotive_quality",
            "phase": "closing",
            "accuracy": 1.0,
            "text": "Thanks for your time.",
        },
    ]
    result = technical_scoring_pipeline(answers)
    assert result.technical_score == 0.0
    assert result.decision == "Weak Technical Fit"
    assert result.scored_answers == []
    assert result.skill_breakdown == {}


def test_pipeline_empty_text_is_valid_not_missing():
    answers = [
        {
            "question_id": "TQ_FOOD_CONC_001",
            "skill_domain": "food_safety_systems",
            "phase": "conceptual",
            "accuracy": 0.0,
            "text": "",
        }
    ]
    result = technical_scoring_pipeline(answers)
    assert len(result.scored_answers) == 1
    assert result.scored_answers[0].final_score == 0.0
