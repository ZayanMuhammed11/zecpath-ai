"""
tests/test_hiring_report_engine.py

Pytest suite for hiring_report_ai.hiring_report_engine (Day 53).
"""

from hiring_report_ai.hiring_report_engine import (
    SUPPORTING_LABELS_NOTE,
    VISUAL_BEHAVIOR_NOTE,
    build_authoritative_recommendation,
    build_behavioral_integrity_notes,
    build_highlights_section,
    build_hiring_report,
    build_round_summary,
    generate_report_text,
)
from hiring_report_ai.hiring_report_models import (
    AuthoritativeRecommendation,
    HighlightsSection,
    HiringIntelligenceReport,
    RoundSummary,
)


# ---------------------------------------------------------------------------
# build_round_summary
# ---------------------------------------------------------------------------


def test_build_round_summary_data_none():
    result = build_round_summary("ats", None, "final_score", "match_label")
    assert result.included is False
    assert result.score is None
    assert result.label is None
    assert result.round_name == "ats"


def test_build_round_summary_data_supplied_both_keys():
    data = {"final_score": 82.5, "match_label": "Strong Match"}
    result = build_round_summary("ats", data, "final_score", "match_label")
    assert result.included is True
    assert result.score == 82.5
    assert result.label == "Strong Match"


def test_build_round_summary_missing_score_key_no_exception():
    data = {"some_other_key": 1}
    result = build_round_summary("technical", data, "technical_score", "decision")
    assert result.included is True
    assert result.score is None
    assert result.label is None


# ---------------------------------------------------------------------------
# build_behavioral_integrity_notes
# ---------------------------------------------------------------------------


def test_build_behavioral_integrity_notes_both_none():
    result = build_behavioral_integrity_notes(None, None)
    assert result.visual_behavior_note == VISUAL_BEHAVIOR_NOTE
    assert result.visual_behavior_score is None
    assert result.visual_behavior_level is None
    assert result.integrity_score is None
    assert result.integrity_risk_level is None
    assert result.integrity_warnings == []


def test_build_behavioral_integrity_notes_both_supplied():
    visual_data = {"visual_behavior_score": 88.0, "level": "High Engagement"}
    integrity_data = {
        "integrity_score": 91.0,
        "risk_level": "Low Risk",
        "warnings": ["minor tab switch detected"],
    }
    result = build_behavioral_integrity_notes(visual_data, integrity_data)
    assert result.visual_behavior_note == VISUAL_BEHAVIOR_NOTE
    assert result.visual_behavior_score == 88.0
    assert result.visual_behavior_level == "High Engagement"
    assert result.integrity_score == 91.0
    assert result.integrity_risk_level == "Low Risk"
    assert result.integrity_warnings == ["minor tab switch detected"]


# ---------------------------------------------------------------------------
# build_highlights_section
# ---------------------------------------------------------------------------


def test_build_highlights_section_none():
    result = build_highlights_section(None)
    assert result.strengths == []
    assert result.weaknesses == []
    assert result.risks == []
    assert result.inconsistencies == []


def test_build_highlights_section_partial():
    hr_summary_data = {"highlights": {"strengths": ["Clear communicator"]}}
    result = build_highlights_section(hr_summary_data)
    assert result.strengths == ["Clear communicator"]
    assert result.weaknesses == []
    assert result.risks == []
    assert result.inconsistencies == []


# ---------------------------------------------------------------------------
# build_authoritative_recommendation
# ---------------------------------------------------------------------------


def test_build_authoritative_recommendation_both_none():
    result = build_authoritative_recommendation(None, None)
    assert result.recommendation is None
    assert result.source == "none available"


def test_build_authoritative_recommendation_only_unified_score():
    unified_score_data = {"recommendation": "selected"}
    result = build_authoritative_recommendation(None, unified_score_data)
    assert result.recommendation == "selected"
    assert "decision_ai" in result.source


def test_build_authoritative_recommendation_both_supplied_final_wins():
    final_decision_data = {"final_recommendation": "hold"}
    unified_score_data = {"recommendation": "selected"}
    result = build_authoritative_recommendation(
        final_decision_data, unified_score_data
    )
    assert result.recommendation == "hold"
    assert result.recommendation != unified_score_data["recommendation"]
    assert "final_decision_ai" in result.source


# ---------------------------------------------------------------------------
# build_hiring_report
# ---------------------------------------------------------------------------


def test_build_hiring_report_zero_optional_arguments():
    report = build_hiring_report(candidate_id="cand-001")
    assert all(r.included is False for r in report.rounds)
    assert report.authoritative_recommendation.recommendation is None
    assert report.authoritative_recommendation.source == "none available"
    assert report.highlights.strengths == []
    assert report.highlights.weaknesses == []
    assert report.highlights.risks == []
    assert report.highlights.inconsistencies == []


def test_build_hiring_report_all_arguments_populated():
    ats_data = {
        "final_score": 88.0,
        "match_label": "Strong Match",
        "shortlisted": True,
        "job_title": "QE Automation Engineer",
    }
    screening_data = {"screening_score": 75.0}
    hr_summary_data = {
        "composite": {"hr_score": 80.0, "decision": "Strong Hire"},
        "highlights": {
            "strengths": ["Strong communicator"],
            "weaknesses": ["Limited domain depth"],
            "risks": ["None flagged"],
            "inconsistencies": [],
        },
    }
    technical_data = {"technical_score": 78.0, "decision": "Strong Technical Fit"}
    machine_test_data = {"final_score": 82.0, "decision": "Strong Practical Fit"}
    unified_score_data = {"recommendation": "selected"}
    final_decision_data = {"final_recommendation": "selected"}
    visual_behavior_data = {"visual_behavior_score": 90.0, "level": "High Engagement"}
    integrity_data = {
        "integrity_score": 95.0,
        "risk_level": "Low Risk",
        "warnings": [],
    }

    report = build_hiring_report(
        candidate_id="cand-002",
        job_title="QE Automation Engineer",
        ats_data=ats_data,
        screening_data=screening_data,
        hr_summary_data=hr_summary_data,
        technical_data=technical_data,
        machine_test_data=machine_test_data,
        unified_score_data=unified_score_data,
        final_decision_data=final_decision_data,
        visual_behavior_data=visual_behavior_data,
        integrity_data=integrity_data,
    )

    assert all(r.included is True for r in report.rounds)

    round_by_name = {r.round_name: r for r in report.rounds}
    assert round_by_name["ats"].score == 88.0
    assert round_by_name["ats"].label == "Strong Match"
    assert round_by_name["screening"].score == 75.0
    assert round_by_name["screening"].label is None
    assert round_by_name["hr_interview"].score == 80.0
    assert round_by_name["hr_interview"].label == "Strong Hire"
    assert round_by_name["technical"].score == 78.0
    assert round_by_name["technical"].label == "Strong Technical Fit"
    assert round_by_name["machine_test"].score == 82.0
    assert round_by_name["machine_test"].label == "Strong Practical Fit"

    assert report.highlights.strengths == ["Strong communicator"]
    assert report.authoritative_recommendation.recommendation == "selected"
    assert "final_decision_ai" in report.authoritative_recommendation.source


def test_build_hiring_report_hr_summary_without_composite():
    hr_summary_data = {"highlights": {"strengths": ["Good rapport"]}}
    report = build_hiring_report(
        candidate_id="cand-003", hr_summary_data=hr_summary_data
    )
    round_by_name = {r.round_name: r for r in report.rounds}
    assert round_by_name["hr_interview"].included is False


# ---------------------------------------------------------------------------
# generate_report_text
# ---------------------------------------------------------------------------


def test_generate_report_text_content():
    rounds = [
        RoundSummary(
            round_name="ats", score=88.0, label="Strong Match", included=True
        ),
        RoundSummary(
            round_name="technical", score=None, label=None, included=False
        ),
    ]
    authoritative_recommendation = AuthoritativeRecommendation(
        recommendation="selected",
        source="final_decision_ai (risk-adjusted final recommendation)",
        rationale="test rationale",
    )
    highlights = HighlightsSection()

    text = generate_report_text(
        candidate_id="cand-004",
        job_title="QE Automation Engineer",
        rounds=rounds,
        authoritative_recommendation=authoritative_recommendation,
        highlights=highlights,
    )

    assert "cand-004" in text
    assert "Strong Match" in text
    assert "technical" not in text


# ---------------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------------


def test_build_hiring_report_returns_hiring_intelligence_report_instance():
    report = build_hiring_report(candidate_id="cand-005")
    assert isinstance(report, HiringIntelligenceReport)


def test_supporting_labels_note_always_exact_constant():
    report_empty = build_hiring_report(candidate_id="cand-006")
    report_populated = build_hiring_report(
        candidate_id="cand-007",
        ats_data={"final_score": 50.0, "match_label": "Weak Match"},
    )
    assert report_empty.supporting_labels_note == SUPPORTING_LABELS_NOTE
    assert report_populated.supporting_labels_note == SUPPORTING_LABELS_NOTE


# ---------------------------------------------------------------------------
# generate_report_text — inconsistencies block (Day 65)
# ---------------------------------------------------------------------------


def test_generate_report_text_includes_inconsistencies_when_present():
    rounds = [
        RoundSummary(
            round_name="ats", score=88.0, label="Strong Match", included=True
        ),
    ]
    authoritative_recommendation = AuthoritativeRecommendation(
        recommendation="selected",
        source="final_decision_ai (risk-adjusted final recommendation)",
        rationale="test rationale",
    )
    highlights = HighlightsSection(
        inconsistencies=["Claimed 5 years experience but resume shows 3"]
    )

    text = generate_report_text(
        candidate_id="cand-008",
        job_title="QE Automation Engineer",
        rounds=rounds,
        authoritative_recommendation=authoritative_recommendation,
        highlights=highlights,
    )

    assert "Inconsistencies:" in text
    assert "Claimed 5 years experience but resume shows 3" in text


def test_generate_report_text_omits_inconsistencies_when_empty():
    rounds = [
        RoundSummary(
            round_name="ats", score=88.0, label="Strong Match", included=True
        ),
    ]
    authoritative_recommendation = AuthoritativeRecommendation(
        recommendation="selected",
        source="final_decision_ai (risk-adjusted final recommendation)",
        rationale="test rationale",
    )
    highlights = HighlightsSection()

    text = generate_report_text(
        candidate_id="cand-009",
        job_title="QE Automation Engineer",
        rounds=rounds,
        authoritative_recommendation=authoritative_recommendation,
        highlights=highlights,
    )

    assert "Inconsistencies:" not in text
