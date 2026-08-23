"""
interview_ai/summary_generator.py

Day 39 Interview Summary Generator.

Converts typed Day 35-38 interview evaluation outputs (HR score,
communication score, confidence/behavior score, optional aptitude
score) into a structured, recruiter-facing InterviewSummary with a
deterministic, template-based natural-language narrative.

This module CONSUMES prior scoring outputs read-only; it does not
rewrite, duplicate, or mutate their scoring logic. Fully isolated:
does not import from screening_ai/, ats_engine/, or scoring/.
"""

from typing import Optional

from interview_ai.aptitude_models import AptitudeScore
from interview_ai.communication_models import CommunicationScore
from interview_ai.confidence_models import ConfidenceBehaviorScore
from interview_ai.hr_scoring_models import HRInterviewScore
from interview_ai.summary_models import (
    CulturalFitIndicator,
    CulturalFitLevel,
    InterviewSummary,
    InterviewSummaryComposite,
    InterviewSummaryHighlights,
)
from utils.logger import get_logger

logger = get_logger(__name__)


def get_overall_decision(score: float) -> str:
    """Map a composite display score to a hiring-decision band.

    Duplicated by value from hr_scoring_engine's existing band names
    and cutoffs for display consistency — deliberately NOT imported,
    per interview_ai's no-cross-file-coupling convention within this
    module (see DAY39_DECISIONS.md).

    Args:
        score: Composite score in [0, 100].

    Returns:
        "Strong Hire" if score >= 75, "Consider" if score >= 55,
        otherwise "Reject".
    """
    if score >= 75:
        return "Strong Hire"
    if score >= 55:
        return "Consider"
    return "Reject"


def compute_cultural_fit(
    behavior: ConfidenceBehaviorScore, hr_result: HRInterviewScore
) -> CulturalFitIndicator:
    """Compute a graduated cultural-fit indicator from upstream signals.

    This replaces manager-sample keyword string-matching with a
    graduated score derived purely from signals already computed by
    upstream Day 36/37 modules — no new text analysis is introduced.

    Starting from a base score of 1.0:
      - Subtract 0.4 if behavior.behavior_flags.contradiction_detected
        is True.
      - Subtract 0.2 if the average of breakdown.consistency across
        hr_result.scored_answers is < 0.7. If scored_answers is empty,
        consistency is treated as 1.0 and this subtraction is skipped.
    The result is clamped to [0, 1] and rounded to 4 d.p.

    Args:
        behavior: Day 36 confidence/behavior output for the interview.
        hr_result: Day 37 aggregated HR interview score.

    Returns:
        A populated CulturalFitIndicator.
    """
    score = 1.0
    contradiction = behavior.behavior_flags.contradiction_detected

    if hr_result.scored_answers:
        avg_consistency = sum(
            answer.breakdown.consistency for answer in hr_result.scored_answers
        ) / len(hr_result.scored_answers)
    else:
        avg_consistency = 1.0

    low_consistency = avg_consistency < 0.7

    if contradiction:
        score -= 0.4
    if low_consistency:
        score -= 0.2

    score = max(0.0, min(1.0, score))
    score = round(score, 4)

    if score >= 0.75:
        level = CulturalFitLevel.good
    elif score >= 0.4:
        level = CulturalFitLevel.moderate
    else:
        level = CulturalFitLevel.low

    contradiction_text = "contradiction detected" if contradiction else "no contradictions detected"
    consistency_text = "consistency low" if low_consistency else "consistency high"
    rationale = f"{contradiction_text}; {consistency_text}"

    logger.debug(
        "compute_cultural_fit -> score=%.4f, level=%s, rationale=%r",
        score,
        level.value,
        rationale,
    )

    return CulturalFitIndicator(level=level, score=score, rationale=rationale)


def extract_inconsistencies(behavior: ConfidenceBehaviorScore) -> list[str]:
    """Extract inconsistency notes from a behavior score's contradiction flag.

    IMPORTANT SCOPE NOTE: This only reflects Day 36's surface-level
    contrast-marker detection (e.g. presence of "but"/"however"). It
    is explicitly NOT a semantic/logical contradiction analysis, and
    the returned string is worded to avoid overstating that
    capability.

    Args:
        behavior: Day 36 confidence/behavior output for the interview.

    Returns:
        A single-item list if a surface contrast marker was flagged,
        otherwise an empty list.
    """
    if behavior.behavior_flags.contradiction_detected:
        return [
            "Surface-level contrast markers (e.g. 'but'/'however') detected "
            "in response — not a semantic contradiction check."
        ]
    return []


def build_highlights(
    hr_result: HRInterviewScore,
    communication: CommunicationScore,
    behavior: ConfidenceBehaviorScore,
) -> InterviewSummaryHighlights:
    """Build strengths/weaknesses/risks/inconsistencies from scoring outputs.

    Every list may end up empty — no placeholder items are inserted
    just to guarantee non-empty output.

    Args:
        hr_result: Day 37 aggregated HR interview score.
        communication: Communication evaluation output.
        behavior: Day 36 confidence/behavior output.

    Returns:
        A populated InterviewSummaryHighlights.
    """
    strengths: list[str] = []
    weaknesses: list[str] = []
    risks: list[str] = []

    if hr_result.hr_score >= 75:
        strengths.append("Strong HR interview performance")
    if communication.level == "Excellent" or communication.communication_score >= 85:
        strengths.append("Excellent communication skills")
    if behavior.behavioral_score >= 75:
        strengths.append("High behavioral confidence")

    if hr_result.hr_score < 55:
        weaknesses.append("Below-average HR interview performance")
    if communication.communication_score < 50:
        weaknesses.append("Weak communication clarity")
    if behavior.behavioral_score < 50:
        weaknesses.append("Low behavioral confidence")

    if behavior.confidence.confidence_score < 50:
        risks.append("Low confidence signal detected")
    if behavior.stress_score < 0.5:
        risks.append("Elevated stress indicators")

    inconsistencies = extract_inconsistencies(behavior)

    logger.debug(
        "build_highlights -> strengths=%d, weaknesses=%d, risks=%d, inconsistencies=%d",
        len(strengths),
        len(weaknesses),
        len(risks),
        len(inconsistencies),
    )

    return InterviewSummaryHighlights(
        strengths=strengths,
        weaknesses=weaknesses,
        risks=risks,
        inconsistencies=inconsistencies,
    )


def build_composite(
    hr_result: HRInterviewScore,
    communication: CommunicationScore,
    behavior: ConfidenceBehaviorScore,
    aptitude: Optional[AptitudeScore] = None,
) -> InterviewSummaryComposite:
    """Build the display-only weighted composite score for an interview.

    overall_score = hr_score * 0.4 + communication_score * 0.3
                    + behavioral_score * 0.3, rounded to 2 d.p.

    aptitude.aptitude_score, if provided, is carried onto the
    composite's aptitude_score field for display only — it is NEVER
    part of the 0.4/0.3/0.3 weighted calculation itself.

    Args:
        hr_result: Day 37 aggregated HR interview score.
        communication: Communication evaluation output.
        behavior: Day 36 confidence/behavior output.
        aptitude: Optional Day 38 aptitude score, display-only.

    Returns:
        A populated InterviewSummaryComposite.
    """
    overall = round(
        hr_result.hr_score * 0.4
        + communication.communication_score * 0.3
        + behavior.behavioral_score * 0.3,
        2,
    )
    decision = get_overall_decision(overall)
    aptitude_score = aptitude.aptitude_score if aptitude is not None else None

    logger.debug(
        "build_composite -> overall_score=%.2f, decision=%s, aptitude_score=%s",
        overall,
        decision,
        aptitude_score,
    )

    return InterviewSummaryComposite(
        overall_score=overall,
        decision=decision,
        hr_score=hr_result.hr_score,
        communication_score=communication.communication_score,
        behavioral_score=behavior.behavioral_score,
        aptitude_score=aptitude_score,
    )


def generate_natural_language_summary(
    highlights: InterviewSummaryHighlights,
    cultural_fit: CulturalFitIndicator,
    composite: InterviewSummaryComposite,
) -> str:
    """Render a deterministic, template-based narrative summary.

    No free-generation and no external calls — pure string formatting,
    mirroring the templated style used elsewhere in interview_ai.

    Args:
        highlights: Strengths/weaknesses/risks/inconsistencies.
        cultural_fit: Graduated cultural-fit indicator.
        composite: Weighted display composite and decision.

    Returns:
        A short narrative paragraph.
    """
    top_strengths = highlights.strengths[:2]
    top_weaknesses = highlights.weaknesses[:2]

    strengths_text = ", ".join(top_strengths) if top_strengths else "no standout strengths identified"
    weaknesses_text = ", ".join(top_weaknesses) if top_weaknesses else "no major weaknesses identified"
    risks_text = ", ".join(highlights.risks) if highlights.risks else "no major risks identified"

    summary = (
        f"Key strengths: {strengths_text}. "
        f"Key weaknesses: {weaknesses_text}. "
        f"Risk flags: {risks_text}. "
        f"Cultural fit is assessed as {cultural_fit.level.value}. "
        f"Overall recommendation: {composite.decision}."
    )

    logger.debug("generate_natural_language_summary -> %r", summary)
    return summary


def generate_interview_summary(
    candidate_id: str,
    hr_result: HRInterviewScore,
    communication: CommunicationScore,
    behavior: ConfidenceBehaviorScore,
    aptitude: Optional[AptitudeScore] = None,
) -> InterviewSummary:
    """Orchestrate the full Day 39 pipeline into a populated InterviewSummary.

    Args:
        candidate_id: Identifier of the candidate.
        hr_result: Day 37 aggregated HR interview score.
        communication: Communication evaluation output.
        behavior: Day 36 confidence/behavior output.
        aptitude: Optional Day 38 aptitude score, display-only.

    Returns:
        A fully populated InterviewSummary.
    """
    logger.info("generate_interview_summary called for candidate_id=%s", candidate_id)

    highlights = build_highlights(hr_result, communication, behavior)
    cultural_fit = compute_cultural_fit(behavior, hr_result)
    composite = build_composite(hr_result, communication, behavior, aptitude)
    narrative = generate_natural_language_summary(highlights, cultural_fit, composite)
    aptitude_score = aptitude.aptitude_score if aptitude is not None else None

    summary = InterviewSummary(
        candidate_id=candidate_id,
        composite=composite,
        highlights=highlights,
        cultural_fit=cultural_fit,
        aptitude_score=aptitude_score,
        natural_language_summary=narrative,
    )

    logger.info(
        "generate_interview_summary -> candidate_id=%s, overall_score=%.2f, decision=%s",
        candidate_id,
        composite.overall_score,
        composite.decision,
    )
    return summary
