"""
tests/test_summary_generator.py

Pure pytest tests for the Day 39 Interview Summary Generator.
No mocking, no random.
"""

import pytest

from interview_ai.aptitude_models import AptitudeScore, AptitudeScoreBreakdown
from interview_ai.communication_models import CommunicationScore, CommunicationScoreBreakdown
from interview_ai.confidence_models import (
    BehaviorFlags,
    ConfidenceBehaviorScore,
    ConfidenceScore,
    ConfidenceSignals,
    SentimentResult,
)
from interview_ai.hr_scoring_models import HRAnswerScore, HRAnswerScoreBreakdown, HRInterviewScore
from interview_ai.summary_generator import (
    build_composite,
    build_highlights,
    compute_cultural_fit,
    extract_inconsistencies,
    generate_interview_summary,
    get_overall_decision,
)
from interview_ai.summary_models import (
    CulturalFitLevel,
    InterviewSummary,
    InterviewSummaryComposite,
    InterviewSummaryHighlights,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_hr_result(hr_score: float, consistencies: list[float]) -> HRInterviewScore:
    scored_answers = [
        HRAnswerScore(
            question_id=f"Q{i}",
            final_score=hr_score,
            breakdown=HRAnswerScoreBreakdown(
                relevance=1.0, communication=1.0, confidence=1.0, consistency=c
            ),
        )
        for i, c in enumerate(consistencies)
    ]
    return HRInterviewScore(hr_score=hr_score, decision="Consider", scored_answers=scored_answers)


def make_communication(score: float, level: str = "Average") -> CommunicationScore:
    return CommunicationScore(
        communication_score=score,
        level=level,
        word_count=50,
        breakdown=CommunicationScoreBreakdown(
            fluency=0.8, grammar=0.8, vocabulary=0.8, clarity=0.8, structure=0.8, filler_penalty=0.0
        ),
    )


def make_behavior(
    behavioral_score: float,
    confidence_score: float = 80.0,
    stress_score: float = 0.8,
    contradiction_detected: bool = False,
) -> ConfidenceBehaviorScore:
    return ConfidenceBehaviorScore(
        confidence=ConfidenceScore(
            confidence_score=confidence_score,
            signals=ConfidenceSignals(hesitation=0.8, repetition=0.8, uncertainty=0.8, pace=0.8),
        ),
        sentiment=SentimentResult(sentiment="Neutral", sentiment_score=0.5),
        behavior_flags=BehaviorFlags(
            uncertainty_detected=False, contradiction_detected=contradiction_detected
        ),
        stress_score=stress_score,
        behavioral_score=behavioral_score,
    )


def make_aptitude(score: float) -> AptitudeScore:
    return AptitudeScore(
        aptitude_score=score,
        breakdown=AptitudeScoreBreakdown(structure=0.8, problem_solving=0.8, decision_quality=0.8),
        word_count=40,
    )


# ---------------------------------------------------------------------------
# get_overall_decision
# ---------------------------------------------------------------------------


def test_get_overall_decision_strong_hire():
    assert get_overall_decision(75) == "Strong Hire"


def test_get_overall_decision_consider():
    assert get_overall_decision(55) == "Consider"


def test_get_overall_decision_reject():
    assert get_overall_decision(54.9) == "Reject"


# ---------------------------------------------------------------------------
# compute_cultural_fit
# ---------------------------------------------------------------------------


def test_cultural_fit_no_contradiction_high_consistency_is_good():
    hr_result = make_hr_result(80, [0.9, 0.95])
    behavior = make_behavior(80, contradiction_detected=False)
    indicator = compute_cultural_fit(behavior, hr_result)
    assert indicator.level == CulturalFitLevel.good
    assert indicator.score == 1.0


def test_cultural_fit_contradiction_lowers_score_and_level():
    hr_result = make_hr_result(80, [0.9, 0.95])
    behavior = make_behavior(80, contradiction_detected=True)
    indicator = compute_cultural_fit(behavior, hr_result)
    assert indicator.score == 0.6
    assert indicator.level == CulturalFitLevel.moderate


def test_cultural_fit_low_consistency_alone_is_moderate():
    hr_result = make_hr_result(80, [0.2, 0.3])
    behavior = make_behavior(80, contradiction_detected=False)
    indicator = compute_cultural_fit(behavior, hr_result)
    assert indicator.score == 0.8
    assert indicator.level == CulturalFitLevel.good


def test_cultural_fit_empty_scored_answers_does_not_raise():
    hr_result = make_hr_result(80, [])
    behavior = make_behavior(80, contradiction_detected=False)
    indicator = compute_cultural_fit(behavior, hr_result)
    assert indicator.score == 1.0


# ---------------------------------------------------------------------------
# extract_inconsistencies
# ---------------------------------------------------------------------------


def test_extract_inconsistencies_true_returns_one_item():
    behavior = make_behavior(80, contradiction_detected=True)
    result = extract_inconsistencies(behavior)
    assert len(result) == 1


def test_extract_inconsistencies_false_returns_empty_list():
    behavior = make_behavior(80, contradiction_detected=False)
    assert extract_inconsistencies(behavior) == []


# ---------------------------------------------------------------------------
# build_highlights
# ---------------------------------------------------------------------------


def test_build_highlights_strengths_populated_on_high_scores():
    hr_result = make_hr_result(80, [0.9])
    communication = make_communication(90, level="Excellent")
    behavior = make_behavior(80)
    highlights = build_highlights(hr_result, communication, behavior)
    assert "Strong HR interview performance" in highlights.strengths
    assert "Excellent communication skills" in highlights.strengths
    assert "High behavioral confidence" in highlights.strengths


def test_build_highlights_weaknesses_populated_on_low_scores():
    hr_result = make_hr_result(30, [0.9])
    communication = make_communication(30, level="Poor")
    behavior = make_behavior(30)
    highlights = build_highlights(hr_result, communication, behavior)
    assert "Below-average HR interview performance" in highlights.weaknesses
    assert "Weak communication clarity" in highlights.weaknesses
    assert "Low behavioral confidence" in highlights.weaknesses


def test_build_highlights_risks_populated_on_low_confidence_and_stress():
    hr_result = make_hr_result(80, [0.9])
    communication = make_communication(80)
    behavior = make_behavior(80, confidence_score=30, stress_score=0.2)
    highlights = build_highlights(hr_result, communication, behavior)
    assert "Low confidence signal detected" in highlights.risks
    assert "Elevated stress indicators" in highlights.risks


def test_build_highlights_empty_lists_when_no_conditions_trigger():
    hr_result = make_hr_result(65, [0.9])
    communication = make_communication(65)
    behavior = make_behavior(65, confidence_score=65, stress_score=0.8)
    highlights = build_highlights(hr_result, communication, behavior)
    assert highlights.strengths == []
    assert highlights.weaknesses == []
    assert highlights.risks == []


# ---------------------------------------------------------------------------
# build_composite
# ---------------------------------------------------------------------------


def test_build_composite_weighted_calculation_correctness():
    hr_result = make_hr_result(80, [0.9])
    communication = make_communication(70)
    behavior = make_behavior(60)
    composite = build_composite(hr_result, communication, behavior)
    expected = round(80 * 0.4 + 70 * 0.3 + 60 * 0.3, 2)
    assert composite.overall_score == expected
    assert isinstance(composite, InterviewSummaryComposite)


def test_build_composite_aptitude_not_reflected_in_overall_score():
    hr_result = make_hr_result(80, [0.9])
    communication = make_communication(70)
    behavior = make_behavior(60)
    without_aptitude = build_composite(hr_result, communication, behavior)
    with_aptitude = build_composite(hr_result, communication, behavior, aptitude=make_aptitude(10))
    assert with_aptitude.overall_score == without_aptitude.overall_score
    assert with_aptitude.aptitude_score == 10
    assert without_aptitude.aptitude_score is None


# ---------------------------------------------------------------------------
# generate_interview_summary (full pipeline)
# ---------------------------------------------------------------------------


def test_generate_interview_summary_returns_instance():
    hr_result = make_hr_result(80, [0.9])
    communication = make_communication(80)
    behavior = make_behavior(80)
    summary = generate_interview_summary("CAND-1", hr_result, communication, behavior)
    assert isinstance(summary, InterviewSummary)
    assert isinstance(summary.highlights, InterviewSummaryHighlights)
    assert isinstance(summary.composite, InterviewSummaryComposite)


def test_generate_interview_summary_aptitude_none_leaves_fields_none():
    hr_result = make_hr_result(80, [0.9])
    communication = make_communication(80)
    behavior = make_behavior(80)
    summary = generate_interview_summary("CAND-2", hr_result, communication, behavior, aptitude=None)
    assert summary.aptitude_score is None
    assert summary.composite.aptitude_score is None


def test_generate_interview_summary_aptitude_provided_does_not_change_overall_score():
    hr_result = make_hr_result(80, [0.9])
    communication = make_communication(80)
    behavior = make_behavior(80)
    without_aptitude = generate_interview_summary("CAND-3", hr_result, communication, behavior)
    with_aptitude = generate_interview_summary(
        "CAND-3", hr_result, communication, behavior, aptitude=make_aptitude(15)
    )
    assert with_aptitude.composite.overall_score == without_aptitude.composite.overall_score
    assert with_aptitude.aptitude_score == 15
    assert with_aptitude.composite.aptitude_score == 15


def test_generate_interview_summary_candidate_id_and_narrative_present():
    hr_result = make_hr_result(80, [0.9])
    communication = make_communication(80)
    behavior = make_behavior(80)
    summary = generate_interview_summary("CAND-4", hr_result, communication, behavior)
    assert summary.candidate_id == "CAND-4"
    assert isinstance(summary.natural_language_summary, str)
    assert len(summary.natural_language_summary) > 0
