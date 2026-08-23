"""Screening report generation layer for the AI screening pipeline.

This module sits after the answer engine (Day 25), scoring engine
(Day 26), and behavior report engine (Day 27). It consumes the plain
dicts produced by each of those layers — one answer, one score, and one
behavior report per question — and aggregates them into a single
screening report for a candidate, plus a plain-text export formatter.
Output of this module feeds the Day 32 full pipeline wiring.
"""

from utils.logger import get_logger

logger = get_logger(__name__)


def generate_screening_report(
    candidate_id: str,
    job_id: str,
    answers: list[dict],
    scores: list[dict],
    behavior_reports: list[dict],
) -> dict:
    """Generate an aggregate screening report for a candidate.

    Zips together parallel lists of answer, score, and behavior dicts
    (one entry per question, aligned by position) and combines them into
    a single report summarizing strengths, risks, missing data, salary
    and availability highlights, confirmed skills, and a final hire
    decision.

    Args:
        candidate_id: Unique identifier of the candidate being screened.
        job_id: Unique identifier of the job the candidate applied for.
        answers: List of answer dicts produced by
            ``screening_ai.answer_engine.process_answer``.
        scores: List of score dicts produced by
            ``screening_ai.scoring_engine.score_answer``.
        behavior_reports: List of behavior dicts produced by
            ``screening_ai.behavior_report.generate_behavior_report``.

    Returns:
        A dictionary with the keys ``candidate_id``, ``job_id``,
        ``final_score``, ``decision``, ``summary`` (containing
        ``strengths``, ``risks``, and ``missing_data``), ``highlights``
        (containing ``salary_expectation``, ``availability``, and
        ``confirmed_skills``), and ``answers``.
    """
    strengths: list[str] = []
    risks: list[str] = []
    missing_data: list[str] = []
    key_answers: list[dict] = []

    # A set is used here, rather than a list, so that the same skill
    # keyword mentioned across multiple answers is only recorded once in
    # the final report's confirmed_skills.
    confirmed_skills: set[str] = set()

    # salary and availability use last-write-wins semantics: if the
    # candidate addresses these topics in more than one answer, the
    # value from the final relevant answer takes precedence.
    salary: str | None = None
    availability: str | None = None

    for ans, score, behavior in zip(answers, scores, behavior_reports):
        key_answers.append(
            {"question_id": ans["question_id"], "answer": ans["original_text"]}
        )

        if score["final_score"] >= 80:
            strengths.append(f"Strong answer in {ans['question_id']}")

        # communication_strength == "Weak" is treated as a risk signal in
        # its own right, regardless of the numeric score, since poor
        # delivery is itself a hiring risk even for a technically correct
        # answer.
        if score["final_score"] < 50 or behavior["communication_strength"] == "Weak":
            risks.append(f"Weak response in {ans['question_id']}")

        # DAY 42 FIX (backlog #7): mirror scoring_engine.py's keyword-match
        # override — a non-empty keywords_found list is evidence the answer
        # IS on-topic even when off_topic=True (Day 25's classify_intent()
        # cannot recognize domain-specific QE terminology). Without this,
        # technically strong QE answers were incorrectly flagged as
        # "Incomplete or off-topic" in the recruiter-facing report even
        # though scoring_engine.py had already correctly credited them via
        # its own override.
        if ans["is_vague"] or (ans["off_topic"] and not ans["keywords_found"]):
            missing_data.append(
                f"Incomplete or off-topic answer in {ans['question_id']}"
            )

        if ans["salary"] is not None:
            salary = ans["salary"]

        if ans["availability"] != "Unknown":
            availability = ans["availability"]

        confirmed_skills.update(ans["keywords_found"])

    # An empty scores list (no answers scored) safely returns a 0.0
    # final_score and a "Reject" decision rather than raising.
    final_score = (
        sum(s["final_score"] for s in scores) / len(scores) if scores else 0.0
    )

    if final_score >= 70:
        decision = "Proceed"
    elif final_score >= 50:
        decision = "Review"
    else:
        decision = "Reject"

    report = {
        "candidate_id": candidate_id,
        "job_id": job_id,
        "final_score": round(final_score, 2),
        "decision": decision,
        "summary": {
            "strengths": strengths,
            "risks": risks,
            "missing_data": missing_data,
        },
        "highlights": {
            "salary_expectation": salary,
            "availability": availability,
            "confirmed_skills": list(confirmed_skills),
        },
        "answers": key_answers,
    }

    logger.info(
        "generate_screening_report candidate_id=%s job_id=%s final_score=%.2f decision=%s",
        candidate_id,
        job_id,
        report["final_score"],
        decision,
    )
    return report


def _format_list_section(title: str, items: list[str]) -> list[str]:
    """Format a titled list of strings as plain-text lines.

    Args:
        title: The section title, rendered as a header line.
        items: The items to render as bullet lines beneath the title.

    Returns:
        A list of plain-text lines for the section, including a
        placeholder line when ``items`` is empty.
    """
    lines = [f"{title}:"]
    if items:
        lines.extend(f"  - {item}" for item in items)
    else:
        lines.append("  (none)")
    return lines


def export_report_text(report: dict) -> str:
    """Format a screening report dict as a plain-text export string.

    This is a plain string formatter only — it does not write to disk
    and has no PDF/docx dependency. File export is handled by the
    Day 32 pipeline wiring.

    Args:
        report: A report dict produced by ``generate_screening_report``.

    Returns:
        A multi-line plain-text string summarizing the candidate_id,
        job_id, final_score, decision, strengths, risks, missing_data,
        salary, availability, and confirmed_skills, with each section
        separated by a dashed line.
    """
    summary = report["summary"]
    highlights = report["highlights"]
    separator = "-" * 40

    lines: list[str] = [
        f"Candidate ID: {report['candidate_id']}",
        f"Job ID: {report['job_id']}",
        f"Final Score: {report['final_score']}",
        f"Decision: {report['decision']}",
        separator,
    ]
    lines.extend(_format_list_section("Strengths", summary["strengths"]))
    lines.append(separator)
    lines.extend(_format_list_section("Risks", summary["risks"]))
    lines.append(separator)
    lines.extend(_format_list_section("Missing Data", summary["missing_data"]))
    lines.append(separator)
    lines.append(f"Salary Expectation: {highlights['salary_expectation']}")
    lines.append(f"Availability: {highlights['availability']}")
    lines.extend(_format_list_section("Confirmed Skills", highlights["confirmed_skills"]))

    text = "\n".join(lines)
    logger.debug("export_report_text generated %d lines", len(lines))
    return text
