"""
hiring_report_ai/hiring_report_engine.py

Day 53 Hiring Intelligence Report compilation engine.

This module performs NO new scoring, thresholding, or decision logic.
It compiles labels/scores that other modules already computed. The
one exception is build_authoritative_recommendation(), which SELECTS
among existing outputs (final_decision_ai -> decision_ai -> none) — it
does not create a new judgment.

screening_ai's real output shape was not available for this build;
only a generic "screening_score" key is read, with no label
(label_key=None). See DAY53_DECISIONS.md for the known gap.

visual_behavior_ai data has no risk semantics and never influences the
authoritative recommendation (same precedent as final_decision_ai/,
Day 52).

MODULE ISOLATION: hiring_report_ai/ has ZERO imports from decision_ai/,
final_decision_ai/, integrity_ai/, visual_behavior_ai/, interview_ai/,
technical_ai/, machine_test_ai/, screening_ai/, ats_engine/, or
scoring/. It only imports from hiring_report_ai.hiring_report_models
(intra-module) and utils.logger. All external data is accepted as
plain caller-supplied dicts.
"""

from typing import Optional

from utils.logger import get_logger

from hiring_report_ai.hiring_report_models import (
    AuthoritativeRecommendation,
    BehavioralIntegrityNotes,
    HighlightsSection,
    HiringIntelligenceReport,
    RoundSummary,
)

logger = get_logger(__name__)


SUPPORTING_LABELS_NOTE = (
    "The figures and labels below reflect each individual round's own "
    "scoring criteria and are shown for context only. They are not "
    "competing conclusions — the Authoritative Recommendation above is "
    "the figure a recruiter should act on."
)

VISUAL_BEHAVIOR_NOTE = (
    "Visual behavior data, where available, reflects engagement only "
    "and carries no risk or scoring implications."
)


def build_round_summary(
    round_name: str,
    data: Optional[dict],
    score_key: str,
    label_key: Optional[str],
) -> RoundSummary:
    """Compile a single round's score/label into a RoundSummary.

    Only whole-round presence/absence matters here (included). A
    partially-populated round dict (e.g. missing score_key) is not an
    error — it simply yields score=None / label=None for that field.
    """

    if data is None:
        return RoundSummary(
            round_name=round_name, score=None, label=None, included=False
        )

    score = data.get(score_key)
    label = data.get(label_key) if label_key is not None else None
    return RoundSummary(
        round_name=round_name, score=score, label=label, included=True
    )


def build_behavioral_integrity_notes(
    visual_behavior_data: Optional[dict] = None,
    integrity_data: Optional[dict] = None,
) -> BehavioralIntegrityNotes:
    """Compile the passthrough visual-behavior and integrity section.

    visual_behavior_note is ALWAYS VISUAL_BEHAVIOR_NOTE, regardless of
    whether visual_behavior_data is supplied.
    """

    visual_behavior_score = None
    visual_behavior_level = None
    if visual_behavior_data is not None:
        visual_behavior_score = visual_behavior_data.get("visual_behavior_score")
        visual_behavior_level = visual_behavior_data.get("level")

    integrity_score = None
    integrity_risk_level = None
    integrity_warnings: list[str] = []
    if integrity_data is not None:
        integrity_score = integrity_data.get("integrity_score")
        integrity_risk_level = integrity_data.get("risk_level")
        integrity_warnings = integrity_data.get("warnings", [])

    return BehavioralIntegrityNotes(
        visual_behavior_score=visual_behavior_score,
        visual_behavior_level=visual_behavior_level,
        visual_behavior_note=VISUAL_BEHAVIOR_NOTE,
        integrity_score=integrity_score,
        integrity_risk_level=integrity_risk_level,
        integrity_warnings=integrity_warnings,
    )


def build_highlights_section(
    hr_summary_data: Optional[dict] = None,
) -> HighlightsSection:
    """Direct passthrough of InterviewSummaryHighlights values, when
    supplied. Adds no new bullets or logic of its own.
    """

    if hr_summary_data is None:
        return HighlightsSection()

    highlights = hr_summary_data.get("highlights", {})
    return HighlightsSection(
        strengths=highlights.get("strengths", []),
        weaknesses=highlights.get("weaknesses", []),
        risks=highlights.get("risks", []),
        inconsistencies=highlights.get("inconsistencies", []),
    )


def build_authoritative_recommendation(
    final_decision_data: Optional[dict] = None,
    unified_score_data: Optional[dict] = None,
) -> AuthoritativeRecommendation:
    """Select — never derive — the single recommendation a recruiter
    should act on.

    Fallback order: final_decision_ai (risk-adjusted, most downstream)
    -> decision_ai (cross-round, no risk adjustment) -> none available.
    Never falls back to any single-round label (ATS match_label, HR
    decision, technical decision, etc.) as authoritative.
    """

    if final_decision_data is not None:
        return AuthoritativeRecommendation(
            recommendation=final_decision_data.get("final_recommendation"),
            source="final_decision_ai (risk-adjusted final recommendation)",
            rationale=(
                "This is the most downstream stage in the hiring pipeline "
                "and the only one that incorporates integrity risk "
                "adjustment; it is treated as authoritative for recruiter "
                "action."
            ),
        )

    if unified_score_data is not None:
        return AuthoritativeRecommendation(
            recommendation=unified_score_data.get("recommendation"),
            source="decision_ai (cross-round recommendation, no risk adjustment applied)",
            rationale=(
                "final_decision_ai/ risk-adjustment data was not available "
                "for this candidate; this is the most complete "
                "recommendation available."
            ),
        )

    return AuthoritativeRecommendation(
        recommendation=None,
        source="none available",
        rationale=(
            "No cross-round or risk-adjusted recommendation data was "
            "supplied for this candidate; see individual round labels "
            "below for available signal."
        ),
    )


def generate_report_text(
    candidate_id: str,
    job_title: Optional[str],
    rounds: list[RoundSummary],
    authoritative_recommendation: AuthoritativeRecommendation,
    highlights: HighlightsSection,
) -> str:
    """Fully deterministic, template-based plain-text recruiter
    summary. Built purely from already-assembled report fields —
    introduces no new value not already present elsewhere.

    Renders "Strengths:", "Weaknesses:", "Risks:", and
    "Inconsistencies:" sections, each only if the corresponding list
    on highlights is non-empty.
    """

    lines: list[str] = []
    lines.append(f"Candidate: {candidate_id}")
    if job_title is not None:
        lines.append(f"Role: {job_title}")

    lines.append("")
    lines.append("Round Summary:")
    for round_summary in rounds:
        if not round_summary.included:
            continue
        lines.append(
            f"  {round_summary.round_name}: {round_summary.score} — {round_summary.label}"
        )

    lines.append("")
    lines.append(
        f"Authoritative Recommendation: {authoritative_recommendation.recommendation} "
        f"(source: {authoritative_recommendation.source})"
    )

    if highlights.strengths:
        lines.append("")
        lines.append("Strengths:")
        for item in highlights.strengths:
            lines.append(f"  - {item}")

    if highlights.weaknesses:
        lines.append("")
        lines.append("Weaknesses:")
        for item in highlights.weaknesses:
            lines.append(f"  - {item}")

    if highlights.risks:
        lines.append("")
        lines.append("Risks:")
        for item in highlights.risks:
            lines.append(f"  - {item}")

    if highlights.inconsistencies:
        lines.append("")
        lines.append("Inconsistencies:")
        for item in highlights.inconsistencies:
            lines.append(f"  - {item}")

    return "\n".join(lines)


def build_hiring_report(
    candidate_id: str,
    job_title: Optional[str] = None,
    ats_data: Optional[dict] = None,
    screening_data: Optional[dict] = None,
    hr_summary_data: Optional[dict] = None,
    technical_data: Optional[dict] = None,
    machine_test_data: Optional[dict] = None,
    unified_score_data: Optional[dict] = None,
    final_decision_data: Optional[dict] = None,
    visual_behavior_data: Optional[dict] = None,
    integrity_data: Optional[dict] = None,
) -> HiringIntelligenceReport:
    """Single public entry point. Compiles a HiringIntelligenceReport
    from the outputs of every existing scoring module.

    Every argument is independently optional — a real candidate may be
    at any point in a 5-round journey. Never raises for a missing
    argument; simply reflects that round/section as not-included/empty.
    """

    logger.info(
        "Building hiring report for candidate_id=%s.", candidate_id
    )

    hr_interview_data = (
        hr_summary_data.get("composite") if hr_summary_data else None
    )

    rounds = [
        build_round_summary("ats", ats_data, "final_score", "match_label"),
        build_round_summary(
            "screening", screening_data, "screening_score", None
        ),
        build_round_summary(
            "hr_interview", hr_interview_data, "hr_score", "decision"
        ),
        build_round_summary(
            "technical", technical_data, "technical_score", "decision"
        ),
        build_round_summary(
            "machine_test", machine_test_data, "final_score", "decision"
        ),
    ]

    highlights = build_highlights_section(hr_summary_data)
    behavioral_integrity_notes = build_behavioral_integrity_notes(
        visual_behavior_data, integrity_data
    )
    authoritative_recommendation = build_authoritative_recommendation(
        final_decision_data, unified_score_data
    )
    supporting_labels_note = SUPPORTING_LABELS_NOTE

    report_text = generate_report_text(
        candidate_id=candidate_id,
        job_title=job_title,
        rounds=rounds,
        authoritative_recommendation=authoritative_recommendation,
        highlights=highlights,
    )

    report = HiringIntelligenceReport(
        candidate_id=candidate_id,
        job_title=job_title,
        rounds=rounds,
        authoritative_recommendation=authoritative_recommendation,
        supporting_labels_note=supporting_labels_note,
        highlights=highlights,
        behavioral_integrity_notes=behavioral_integrity_notes,
        report_text=report_text,
    )

    logger.info(
        "Hiring report built for candidate_id=%s; authoritative_recommendation=%s (source=%s).",
        candidate_id,
        authoritative_recommendation.recommendation,
        authoritative_recommendation.source,
    )

    return report
