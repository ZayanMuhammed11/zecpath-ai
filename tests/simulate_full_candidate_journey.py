"""
tests/simulate_full_candidate_journey.py

Demonstration / calibration script for Zecpath AI — Sprint 3, Day 45.

This script demonstrates the real, tested pipeline functions (HR interview
scoring from interview_ai/, plus cross-round unified scoring from
decision_ai/) running end-to-end on hand-authored, fixed demo candidate
profiles. It is NOT a claim of production status, NOT connected to any live
API, does NOT use real candidate data, and its results are NOT a validated
claim of real-world accuracy.

This is NOT a pytest file (same category as tests/simulate_hr_interview.py
from a prior day) — it is a manual demonstration/calibration script, and it
is deliberately excluded from the pytest suite. Run it manually with:

    python -m tests.simulate_full_candidate_journey

No random module is used anywhere in this script; all demo data below is
fixed and hand-authored.
"""

from typing import Any, Dict, List, Optional

from decision_ai.decision_models import RoleLevel as DecisionRoleLevel, RoundScores
from decision_ai.unified_scoring_engine import unified_scoring_pipeline
from interview_ai.behavior_analyzer import analyze_behavior
from interview_ai.communication_engine import calculate_communication_score
from interview_ai.communication_models import CommunicationScore
from interview_ai.confidence_models import ConfidenceBehaviorScore
from interview_ai.hr_scoring_engine import hr_scoring_pipeline
from interview_ai.hr_scoring_models import HRInterviewScore
from interview_ai.interview_models import RoleLevel as InterviewRoleLevel
from interview_ai.summary_generator import generate_interview_summary
from utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Demo profiles
# ---------------------------------------------------------------------------


def build_demo_profiles() -> List[Dict[str, Any]]:
    """Build the fixed set of hand-authored demo candidate profiles.

    Four profiles are defined, covering a senior candidate with a full
    three-round journey, a mid-level candidate with a missing screening
    round (to exercise decision_ai's proportional weight redistribution
    path), a vague fresher candidate, and a hesitant mid-level candidate.

    No random module is used — every value below is fixed and authored
    by hand for calibration/demonstration purposes only.

    Returns:
        A list of profile dicts, each with the keys: candidate_id,
        role_level (InterviewRoleLevel), ats_score, screening_score
        (float or None), question_id, answer_text, duration_seconds,
        relevance_score, is_vague.
    """
    return [
        {
            "candidate_id": "senior_full_journey",
            "role_level": InterviewRoleLevel.senior,
            "ats_score": 88.0,
            "screening_score": 82.0,
            "question_id": "Q1",
            "answer_text": (
                "In my most recent role I led the redesign of our "
                "order-processing pipeline to handle a five-times increase "
                "in daily transaction volume. First, I profiled the "
                "existing bottlenecks and identified the database layer as "
                "the primary constraint. Then, I introduced a caching "
                "layer and re-architected the write path to use "
                "asynchronous batching. As a result, average processing "
                "latency dropped by sixty percent. I coordinated the "
                "rollout across two teams and established clear ownership "
                "for each new service boundary. Because reliability "
                "mattered most during the transition, I introduced "
                "automated regression tests covering every critical path "
                "before deployment. Finally, I documented the new "
                "architecture so the rest of the team could maintain it "
                "independently going forward."
            ),
            "duration_seconds": 42.0,
            "relevance_score": 0.92,
            "is_vague": False,
        },
        {
            "candidate_id": "mid_partial_journey",
            "role_level": InterviewRoleLevel.mid,
            "ats_score": 68.0,
            "screening_score": None,
            "question_id": "Q1",
            "answer_text": (
                "In my current role I mostly work on backend APIs for an "
                "internal tools team. I have handled a few production "
                "incidents, and I usually start by checking the logs and "
                "recent deployments to narrow down the cause. For example, "
                "last quarter I traced a recurring timeout issue back to a "
                "misconfigured connection pool and fixed it by adjusting "
                "the pool size and adding better monitoring around it."
            ),
            "duration_seconds": 28.0,
            "relevance_score": 0.75,
            "is_vague": False,
        },
        {
            "candidate_id": "fresher_full_journey",
            "role_level": InterviewRoleLevel.fresher,
            "ats_score": 45.0,
            "screening_score": 50.0,
            "question_id": "Q1",
            "answer_text": (
                "I built a small web app during my final year project. It "
                "let users track their expenses. I mostly worked on the "
                "frontend part."
            ),
            "duration_seconds": 9.0,
            "relevance_score": 0.45,
            "is_vague": True,
        },
        {
            "candidate_id": "hesitant_mid_full_journey",
            "role_level": InterviewRoleLevel.mid,
            "ats_score": 60.0,
            "screening_score": 58.0,
            "question_id": "Q1",
            "answer_text": (
                "Um, so I think I worked on something similar once, but "
                "I'm not totally sure it's the same kind of problem. It "
                "was, like, a caching issue maybe, or possibly something "
                "with the database, I don't know. We eventually fixed it, "
                "I guess, after some trial and error."
            ),
            "duration_seconds": 33.0,
            "relevance_score": 0.55,
            "is_vague": True,
        },
    ]


# ---------------------------------------------------------------------------
# Pipeline orchestration
# ---------------------------------------------------------------------------


def run_candidate_pipeline(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Run the full HR-interview-plus-unified-scoring pipeline for one profile.

    Mirrors the real, working call order used in the project's existing
    Day 40 HR interview simulation script:
        1. calculate_communication_score
        2. analyze_behavior
        3. build a single answer dict from the communication/behavior output
        4. hr_scoring_pipeline
        5. generate_interview_summary
        6. build the decision_ai RoleLevel explicitly from the interview_ai
           RoleLevel's value (the two RoleLevel enums are independently
           defined and are never used interchangeably)
        7. build RoundScores
        8. unified_scoring_pipeline

    Args:
        profile: One demo profile dict, as produced by build_demo_profiles().

    Returns:
        A dict with keys: communication, behavior, hr_result, summary,
        decision_role, round_scores, unified — the full set of typed
        outputs produced along the pipeline for this candidate.
    """
    candidate_id: str = profile["candidate_id"]
    role_level: InterviewRoleLevel = profile["role_level"]
    answer_text: str = profile["answer_text"]
    duration_seconds: float = profile["duration_seconds"]

    logger.info("Running full candidate journey for candidate_id=%s", candidate_id)

    # 1. Communication scoring
    communication: CommunicationScore = calculate_communication_score(answer_text)

    # 2. Confidence / behavior scoring
    behavior: ConfidenceBehaviorScore = analyze_behavior(answer_text, duration_seconds)

    # 3. Build the single answer dict expected by hr_scoring_pipeline
    answer_dict: Dict[str, Any] = {
        "question_id": profile["question_id"],
        "relevance_score": profile["relevance_score"],
        "communication_score": communication.communication_score / 100.0,
        "confidence_score": behavior.confidence.confidence_score / 100.0,
        "contradiction_detected": behavior.behavior_flags.contradiction_detected,
        "is_vague": profile["is_vague"],
    }

    # 4. HR interview scoring
    hr_result: HRInterviewScore = hr_scoring_pipeline([answer_dict], role_level=role_level)

    # 5. Recruiter-facing interview summary (no aptitude round in this demo)
    summary = generate_interview_summary(candidate_id, hr_result, communication, behavior)

    # 6. Explicit cross-enum construction: decision_ai.RoleLevel is NOT the
    # same class as interview_ai.RoleLevel, even though their string values
    # line up. Always construct it explicitly from the value.
    decision_role: DecisionRoleLevel = DecisionRoleLevel(role_level.value)

    # 7. Assemble the raw round scores for the unified engine
    round_scores = RoundScores(
        ats_score=profile["ats_score"],
        screening_score=profile["screening_score"],
        hr_score=hr_result.hr_score,
    )

    # 8. Cross-round unified scoring
    unified = unified_scoring_pipeline(candidate_id, round_scores, decision_role)

    return {
        "communication": communication,
        "behavior": behavior,
        "hr_result": hr_result,
        "summary": summary,
        "decision_role": decision_role,
        "round_scores": round_scores,
        "unified": unified,
    }


# ---------------------------------------------------------------------------
# Output rendering
# ---------------------------------------------------------------------------


def print_candidate_report(profile: Dict[str, Any], result: Dict[str, Any]) -> None:
    """Print a single, clearly-separated report block for one candidate.

    Args:
        profile: The demo profile dict for this candidate.
        result: The dict returned by run_candidate_pipeline() for this
            candidate.
    """
    candidate_id: str = profile["candidate_id"]
    role_level: InterviewRoleLevel = profile["role_level"]
    communication: CommunicationScore = result["communication"]
    behavior: ConfidenceBehaviorScore = result["behavior"]
    hr_result: HRInterviewScore = result["hr_result"]
    summary = result["summary"]
    unified = result["unified"]

    print("=" * 78)
    print(f"CANDIDATE: {candidate_id}  (role_level={role_level.value})")
    print("=" * 78)

    print("\n-- Communication / Confidence / Behavior --")
    print(f"  communication_score      : {communication.communication_score}")
    print(f"  confidence_score          : {behavior.confidence.confidence_score}")
    print(f"  behavioral_score          : {behavior.behavioral_score}")
    print(f"  contradiction_detected    : {behavior.behavior_flags.contradiction_detected}")

    print("\n-- HR Interview Scoring --")
    print(f"  hr_score                  : {hr_result.hr_score}")
    print(f"  hr_decision                : {hr_result.decision}")

    print("\n-- HR Interview Summary --")
    print(f"  {summary.natural_language_summary}")

    print("\n-- CROSS-ROUND UNIFIED SCORING --")
    print(f"  rounds_included            : {unified.breakdown.rounds_included}")
    print(f"  rounds_missing              : {unified.breakdown.rounds_missing}")
    print("  per-round breakdown:")
    for contribution in unified.breakdown.contributions:
        print(
            f"    - {contribution.round_name:<10} "
            f"raw_score={contribution.raw_score:>6.2f}  "
            f"weight_used={contribution.weight_used:.4f}  "
            f"weighted_contribution={contribution.weighted_contribution:.4f}"
        )
    print(f"  final_score                 : {unified.final_score}")
    print(f"  recommendation               : {unified.recommendation}")
    print(f"  confidence                   : {unified.confidence}")
    print(
        f"  hiring_fit                   : "
        f"{unified.hiring_fit.hiring_fit_percentage}% "
        f"({unified.hiring_fit.fit_category})"
    )
    print(f"  reasoning                    : {unified.reasoning}")
    print()


def print_summary_table(
    profiles: List[Dict[str, Any]], results: List[Dict[str, Any]]
) -> None:
    """Print a final summary table across all demo candidates.

    Args:
        profiles: The list of demo profile dicts, in the same order as
            `results`.
        results: The list of per-candidate result dicts returned by
            run_candidate_pipeline(), in the same order as `profiles`.
    """
    print("=" * 78)
    print("SUMMARY TABLE — ALL CANDIDATES")
    print("=" * 78)

    header = (
        f"{'candidate_id':<28} {'hr_decision':<14} "
        f"{'unified_recommendation':<24} {'unified_confidence':<20} "
        f"{'rounds_included'}"
    )
    print(header)
    print("-" * len(header))

    for profile, result in zip(profiles, results):
        hr_result: HRInterviewScore = result["hr_result"]
        unified = result["unified"]
        rounds_included_count = len(unified.breakdown.rounds_included)
        print(
            f"{profile['candidate_id']:<28} {hr_result.decision:<14} "
            f"{unified.recommendation:<24} {unified.confidence:<20} "
            f"{rounds_included_count}"
        )
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the full candidate journey demonstration for all demo profiles.

    Runs run_candidate_pipeline() for each fixed demo profile, prints a
    detailed report block per candidate, and finishes with a summary table
    across all candidates. Purely a demonstration of the existing, tested
    HR scoring and unified scoring pipelines on authored demo data — not a
    claim of production readiness or real-world accuracy.
    """
    logger.info("Starting full candidate journey demonstration")

    profiles = build_demo_profiles()
    results: List[Dict[str, Any]] = []

    for profile in profiles:
        result = run_candidate_pipeline(profile)
        results.append(result)
        print_candidate_report(profile, result)

    print_summary_table(profiles, results)

    logger.info("Completed full candidate journey demonstration")


if __name__ == "__main__":
    main()
