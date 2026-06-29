"""Day 30 — Screening System Testing & Optimization.

Standalone simulation/validation script (NOT a pytest file). Run directly with:

    python tests/simulate_screening.py

This is the first end-to-end wiring of the six Sprint 2 screening modules built on
Days 24-28 plus the conversation flow state machine from Day 29:

    Day 24 - screening_ai.stt_processor.clean_transcript
    Day 25 - screening_ai.answer_engine.process_answer
    Day 26 - screening_ai.scoring_engine.score_answer
    Day 27 - screening_ai.behavior_report.generate_behavior_report
    Day 28 - screening_ai.report_generator.generate_screening_report
    Day 29 - screening_ai.conversation_flow.ConversationStateMachine

None of these modules have run together before, so this script's job is to surface
integration and calibration problems, not to fix them.

KEY DECISIONS (see also inline comments below):
- Synthetic answers are used instead of real candidate data. Sprint 1's 20 QE
  candidates only exist as PDF resumes, not voice/text screening answers, so this
  is the first dataset of its kind for the screening pipeline.
- qa_pairs whose STT status is not "processed" are skipped entirely rather than
  scored with empty/garbage text. This prevents Day 26's scoring engine from
  scoring garbage-in on silence or poor-audio inputs.
- This script only *surfaces* calibration issues for discussion. It does NOT
  auto-tune any thresholds in the scoring or decision logic — any threshold
  changes are a separate decision made after a human reviews this output.
- This is the first time all Sprint 2 modules (Days 24-29) run together, so any
  exception raised here is treated as an integration bug requiring root-cause
  analysis across modules, not a bug in any single module taken in isolation.
  For that reason, module calls below are intentionally NOT wrapped in
  try/except: letting exceptions propagate with full tracebacks is what makes
  root-causing them possible.
- ConversationStateMachine (Day 29) is not driven directly in the per-question
  loop below. Its public API beyond the `ConversationStateMachine(questions)`
  constructor was not specified for this task, and the per-qa_pair processing
  steps were given explicitly (clean -> process -> score -> behavior -> collect)
  without reference to conversation state transitions. Question ordering is
  fixed by the qa_pairs list itself instead. If Day 29 exposes flow-control
  behavior that should gate which questions get asked, that is a follow-up
  wiring task once its API is confirmed.

This script does not add to or modify the pytest suite. Full pytest suite
remains at 167 passed.
"""

from __future__ import annotations

from typing import Any

from screening_ai.answer_engine import process_answer
from screening_ai.behavior_report import generate_behavior_report
from screening_ai.report_generator import generate_screening_report
from screening_ai.scoring_engine import score_answer
from screening_ai.stt_processor import clean_transcript
from utils.logger import get_logger

logger = get_logger(__name__)

# Heuristic threshold used only by identify_threshold_issues() below to flag a
# "very low" final_score for the silent candidate. Not used anywhere in scoring.
_LOW_SCORE_THRESHOLD = 0.2

JOB_ID = "qe-engineer-req-2031"

# Shared bank of QE screening questions reused across all synthetic candidates.
# Real QE terminology (FMEA, APQP, PPAP, SPC, CAPA, 8D, RCA) is used in both the
# expected_keywords and the synthetic answer text so Day 25's keyword matching
# has something real to find.
# expected_intent values were originally "explain_process"/"describe_experience" —
# invented labels that do not exist in Day 25's INTENT_MAP (screening_ai/answer_engine.py).
# classify_intent() can only return: introduction, experience, skills, salary,
# availability, education, location, or unknown. Using non-existent labels caused
# every QE technical answer to be flagged off_topic=True regardless of answer quality.
# Fixed to "skills" — the correct INTENT_MAP category for hands-on technical/tool
# process questions (FMEA, APQP, SPC, CAPA, PPAP are all QE tools/methodologies).
_QUESTION_BANK: list[dict[str, Any]] = [
    {
        "question_id": "q1_fmea",
        "expected_keywords": ["FMEA", "failure mode", "risk"],
        "expected_intent": "skills",
    },
    {
        "question_id": "q2_apqp",
        "expected_keywords": ["APQP", "planning", "quality"],
        "expected_intent": "skills",
    },
    {
        "question_id": "q3_spc",
        "expected_keywords": ["SPC", "control chart", "variation"],
        "expected_intent": "skills",
    },
    {
        "question_id": "q4_capa_rca",
        "expected_keywords": ["CAPA", "RCA", "root cause"],
        "expected_intent": "skills",
    },
    {
        "question_id": "q5_ppap_8d",
        "expected_keywords": ["PPAP", "8D"],
        "expected_intent": "skills",
    },
]


def _qa_pair(question_index: int, audio_text: str, confidence: float) -> dict[str, Any]:
    """Build a single qa_pair dict by merging question-bank metadata with an answer.

    Args:
        question_index: Index into _QUESTION_BANK identifying which question this
            answer responds to.
        audio_text: Raw (pre-cleaning) STT transcript text for this answer.
        confidence: Simulated STT confidence score for this answer, in [0, 1].

    Returns:
        A qa_pair dict with question_id, audio_text, confidence, expected_keywords,
        and expected_intent, ready to be consumed by run_candidate_simulation().
    """
    question = _QUESTION_BANK[question_index]
    return {
        "question_id": question["question_id"],
        "audio_text": audio_text,
        "confidence": confidence,
        "expected_keywords": question["expected_keywords"],
        "expected_intent": question["expected_intent"],
    }


def _confident_qe_senior_qa_pairs() -> list[dict[str, Any]]:
    """Detailed, on-topic, QE-specific answers with no hedging and clean audio."""
    return [
        _qa_pair(
            0,
            "Sure. For a new component design I pull together the cross-functional team "
            "and walk the design FMEA line by line, scoring severity, occurrence, and "
            "detection for every failure mode before drawings ever get released. High "
            "RPN items get a mitigation plan and an owner before sign-off.",
            0.97,
        ),
        _qa_pair(
            1,
            "At my last company I owned APQP for three new product launches, running all "
            "five phases from planning through production part approval, and I kept the "
            "control plan synced with the FMEA the whole way through.",
            0.96,
        ),
        _qa_pair(
            2,
            "I set up SPC charts on the critical-to-quality dimensions, mostly X-bar-R "
            "charts, and review them daily for points outside control limits or runs "
            "that signal special cause variation before it turns into scrap.",
            0.95,
        ),
        _qa_pair(
            3,
            "I led a CAPA after a field-return spike. The root cause analysis used a "
            "fishbone diagram and five whys, traced it to a fixture wear issue, and I "
            "verified the fix held for ninety days before closing it out.",
            0.96,
        ),
        _qa_pair(
            4,
            "For a PPAP submission tied to an open customer complaint, I'd run the 8D in "
            "parallel, containing the issue at D3 while finishing the PPAP elements so "
            "the submission and the corrective action land together.",
            0.97,
        ),
    ]


def _hesitant_qe_mid_qa_pairs() -> list[dict[str, Any]]:
    """Shorter mid-level answers with hedging language, moderate STT confidence."""
    return [
        _qa_pair(
            0,
            "Um, I think for an FMEA you'd look at, like, the failure modes and maybe "
            "rank them by risk? I've helped with one but I wasn't really leading it.",
            0.83,
        ),
        _qa_pair(
            1,
            "I think we used APQP at my last job, maybe for the planning phase, but I'm "
            "not totally sure I touched all of it myself.",
            0.81,
        ),
        _qa_pair(
            2,
            "I've seen SPC charts before, I think they show if the process is, like, in "
            "control or not? I'd probably need to double check before relying on them.",
            0.80,
        ),
        _qa_pair(
            3,
            "Maybe a CAPA I worked on... I think there was some kind of root cause thing "
            "involved, possibly a five whys, but I don't remember the details well.",
            0.82,
        ),
        _qa_pair(
            4,
            "I think PPAP and 8D are both customer-facing things, maybe related to "
            "complaints? I haven't run one of those myself though.",
            0.79,
        ),
    ]


def _vague_responder_qa_pairs() -> list[dict[str, Any]]:
    """Off-topic or very short answers; STT itself works fine, content does not."""
    return [
        _qa_pair(0, "That's a good question, I'd have to think about it.", 0.88),
        _qa_pair(1, "I'm not sure, I worked at a few different places.", 0.86),
        _qa_pair(2, "Honestly I don't really remember the charts we used.", 0.87),
        _qa_pair(3, "We did stuff like that sometimes I guess.", 0.85),
        _qa_pair(4, "I'd rather talk about my favorite hobbies if that's okay.", 0.89),
    ]


def _silent_candidate_qa_pairs() -> list[dict[str, Any]]:
    """Empty or near-empty answers paired with low confidence, triggering STT issues."""
    return [
        _qa_pair(0, "", 0.12),
        _qa_pair(1, "...", 0.15),
        _qa_pair(2, "um", 0.18),
        _qa_pair(3, "", 0.10),
        _qa_pair(4, "[inaudible]", 0.14),
    ]


def _build_candidate_profiles() -> list[tuple[str, str, list[dict[str, Any]]]]:
    """Assemble the 4 synthetic candidate profiles used by this simulation.

    Returns:
        A list of (candidate_id, job_id, qa_pairs) tuples, one per candidate type.
    """
    return [
        ("confident_qe_senior", JOB_ID, _confident_qe_senior_qa_pairs()),
        ("hesitant_qe_mid", JOB_ID, _hesitant_qe_mid_qa_pairs()),
        ("vague_responder", JOB_ID, _vague_responder_qa_pairs()),
        ("silent_candidate", JOB_ID, _silent_candidate_qa_pairs()),
    ]


def run_candidate_simulation(
    candidate_id: str, job_id: str, qa_pairs: list[dict[str, Any]]
) -> dict[str, Any]:
    """Run one synthetic candidate's qa_pairs through the full screening pipeline.

    For each qa_pair: clean the raw STT transcript (Day 24), and if it comes back
    "processed", run it through answer processing (Day 25), scoring (Day 26), and
    behavior analysis (Day 27). qa_pairs whose STT status is not "processed" are
    skipped entirely — see module docstring for why. All collected results are
    finally compiled into a screening report (Day 28).

    Args:
        candidate_id: Identifier for the synthetic candidate.
        job_id: Identifier for the job this candidate is being screened against.
        qa_pairs: List of dicts each containing question_id, audio_text,
            confidence, expected_keywords, and expected_intent.

    Returns:
        The full report dict from generate_screening_report(), augmented with
        two script-level fields used only by this simulation's own summary
        table and calibration checks (not part of Day 28's own report schema):
        "skipped_qa_pairs" (int) and "first_communication_strength" (the
        communication_strength of the first successfully processed answer, or
        None if every qa_pair was skipped).
    """
    answers: list[dict[str, Any]] = []
    scores: list[dict[str, Any]] = []
    behavior_reports: list[dict[str, Any]] = []
    skipped_count = 0

    for qa_pair in qa_pairs:
        question_id = qa_pair["question_id"]
        audio_text = qa_pair["audio_text"]
        confidence = qa_pair["confidence"]
        expected_keywords = qa_pair.get("expected_keywords")
        expected_intent = qa_pair.get("expected_intent")

        # Day 24: clean the raw transcript before anything downstream sees it.
        stt_result = clean_transcript(audio_text, confidence)

        if stt_result["status"] != "processed":
            skipped_count += 1
            logger.info(
                "candidate_id=%s question_id=%s skipped: STT status=%s issue=%s",
                candidate_id,
                question_id,
                stt_result["status"],
                stt_result.get("issue"),
            )
            continue

        clean_text = stt_result["clean_text"]

        # Day 25: structure the cleaned answer text.
        answer_result = process_answer(
            question_id,
            clean_text,
            expected_keywords=expected_keywords,
            expected_intent=expected_intent,
        )

        # Day 26: score the structured answer.
        score_result = score_answer(answer_result)

        # Day 27: behavioral signal off the same cleaned text.
        behavior_result = generate_behavior_report(clean_text, duration_seconds=8)

        answers.append(answer_result)
        scores.append(score_result)
        behavior_reports.append(behavior_result)

    logger.info(
        "candidate_id=%s: processed %d/%d qa_pairs, skipped %d due to STT issues",
        candidate_id,
        len(answers),
        len(qa_pairs),
        skipped_count,
    )

    # Day 28: compile everything collected above into the final screening report.
    report = generate_screening_report(candidate_id, job_id, answers, scores, behavior_reports)

    # Script-level augmentation for the summary table / calibration checks below.
    # These two fields are not part of Day 28's own report contract.
    report["skipped_qa_pairs"] = skipped_count
    report["first_communication_strength"] = (
        behavior_reports[0]["communication_strength"] if behavior_reports else None
    )

    return report


def _print_summary_table(reports: list[dict[str, Any]]) -> None:
    """Print a formatted console summary table for a list of screening reports.

    Args:
        reports: List of report dicts as returned by run_candidate_simulation().
    """
    header = (
        f"{'candidate_id':<22} {'final_score':>11} {'decision':<10} "
        f"{'comm_strength':<14} {'skipped':>7}"
    )
    print("\n=== Candidate Simulation Summary ===")
    print(header)
    print("-" * len(header))

    for report in reports:
        candidate_id = report.get("candidate_id", "UNKNOWN")
        final_score = report.get("final_score", "N/A")
        decision = report.get("decision", "N/A")
        comm_strength = report.get("first_communication_strength", "N/A")
        skipped = report.get("skipped_qa_pairs", 0)
        print(
            f"{candidate_id:<22} {str(final_score):>11} {str(decision):<10} "
            f"{str(comm_strength):<14} {skipped:>7}"
        )


def run_all_simulations() -> list[dict[str, Any]]:
    """Run all 4 synthetic candidate profiles through run_candidate_simulation().

    Prints a formatted summary table to the console as a side effect.

    Returns:
        List of the 4 full report dicts, one per candidate profile, in the same
        order as _build_candidate_profiles().
    """
    candidate_profiles = _build_candidate_profiles()
    reports: list[dict[str, Any]] = []

    for candidate_id, job_id, qa_pairs in candidate_profiles:
        report = run_candidate_simulation(candidate_id, job_id, qa_pairs)
        reports.append(report)

    _print_summary_table(reports)
    return reports


def identify_threshold_issues(reports: list[dict[str, Any]]) -> list[str]:
    """Flag scoring/decision calibration problems across the 4 simulated reports.

    This function only flags issues for a human to review — it does not change
    any thresholds or scoring logic itself.

    Checks performed:
        - confident_qe_senior should get decision == "Proceed".
        - silent_candidate should get decision == "Reject" or a very low
          final_score (below _LOW_SCORE_THRESHOLD).
        - No report should have final_score == 0.0 with a decision other than
          "Reject" (an internally inconsistent result).

    Args:
        reports: List of report dicts as returned by run_candidate_simulation(),
            expected to contain one report per candidate type from
            _build_candidate_profiles().

    Returns:
        List of human-readable issue strings. Empty list if no issues found.
    """
    issues: list[str] = []
    reports_by_id = {report.get("candidate_id"): report for report in reports}

    confident = reports_by_id.get("confident_qe_senior")
    if confident is not None:
        decision = confident.get("decision")
        if decision != "Proceed":
            issues.append(
                "confident_qe_senior expected decision='Proceed' but got "
                f"'{decision}' (final_score={confident.get('final_score')})"
            )
    else:
        issues.append("confident_qe_senior report missing from results")

    silent = reports_by_id.get("silent_candidate")
    if silent is not None:
        decision = silent.get("decision")
        final_score = silent.get("final_score")
        score_is_low = final_score is not None and final_score < _LOW_SCORE_THRESHOLD
        if decision != "Reject" and not score_is_low:
            issues.append(
                "silent_candidate expected decision='Reject' or final_score < "
                f"{_LOW_SCORE_THRESHOLD} but got decision='{decision}', "
                f"final_score={final_score}"
            )
    else:
        issues.append("silent_candidate report missing from results")

    for report in reports:
        final_score = report.get("final_score")
        decision = report.get("decision")
        if final_score == 0.0 and decision != "Reject":
            issues.append(
                f"{report.get('candidate_id', 'UNKNOWN')} has final_score=0.0 but "
                f"decision='{decision}' instead of 'Reject' (inconsistent "
                "scoring/decision logic)"
            )

    return issues


if __name__ == "__main__":
    all_reports = run_all_simulations()
    calibration_issues = identify_threshold_issues(all_reports)

    print("\n=== Calibration Issues ===")
    if calibration_issues:
        for issue in calibration_issues:
            print(f"  - {issue}")
    else:
        print("No calibration issues detected")
