"""
tests/simulate_hr_interview.py

Day 40 — HR Interview Simulation.

Standalone calibration/sanity-testing script (NOT a pytest file), mirroring
the Day 30 tests/simulate_screening.py precedent. Runs 4 fixed synthetic
candidate profiles through the REAL Day 35-39 pipeline end to end
(communication scoring -> confidence/behavior analysis -> role-weighted HR
scoring -> interview summary generation) and reports the actual output.

IMPORTANT — SCOPE OF THIS SCRIPT:
    This is calibration/sanity testing against our OWN authored
    expectations. It is NOT a claim of validated real-world accuracy.
    There is no real human-evaluator data available anywhere in this
    project, so no "vs human evaluation" accuracy number is computed,
    claimed, or fabricated anywhere in this script or its output.

    Each EXPECTED_OUTCOME entry is our own stated design intent for how
    the current scoring weights *should* behave on a given profile — it
    is a design check, not ground truth. If the real pipeline disagrees
    with an authored expectation, that disagreement is printed as a
    genuine finding, not suppressed, "corrected", or explained away.

Run with:
    python -m tests.simulate_hr_interview

Requires tests/__init__.py to already exist.
"""

from __future__ import annotations

from typing import TypedDict

from interview_ai.behavior_analyzer import analyze_behavior
from interview_ai.communication_engine import calculate_communication_score
from interview_ai.confidence_models import ConfidenceBehaviorScore
from interview_ai.communication_models import CommunicationScore
from interview_ai.hr_scoring_engine import hr_scoring_pipeline
from interview_ai.hr_scoring_models import HRInterviewScore
from interview_ai.interview_models import RoleLevel
from interview_ai.summary_generator import generate_interview_summary
from utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Fixed synthetic candidate profiles (no randomness anywhere)
# ---------------------------------------------------------------------------


class CandidateProfile(TypedDict):
    candidate_id: str
    role_level: RoleLevel
    answer_text: str
    duration_seconds: float
    question_id: str
    relevance_score: float
    is_vague: bool


PROFILES: list[CandidateProfile] = [
    {
        "candidate_id": "confident_senior",
        "role_level": RoleLevel.senior,
        "answer_text": (
            "In my last role as a senior backend engineer, I led the migration of our "
            "monolithic service to a microservices architecture. First, I identified the "
            "highest-risk components. Then, I designed a phased rollout plan with clear "
            "rollback points. As a result, we reduced deployment failures by forty percent. "
            "I coordinated closely with three teams, and I established clear ownership "
            "boundaries for each service. Because reliability was critical, I introduced "
            "automated integration tests for every new endpoint. Finally, I documented the "
            "entire process so future engineers could extend it confidently. I am confident "
            "this approach will scale well as the platform grows."
        ),
        # 101 words / 40s = 2.525 wps, inside confidence_analyzer's 1.5-3.0 ideal band.
        "duration_seconds": 40.0,
        "question_id": "Q1",
        "relevance_score": 0.95,
        "is_vague": False,
    },
    {
        "candidate_id": "hesitant_mid",
        "role_level": RoleLevel.mid,
        "answer_text": (
            "Um, so I worked on a project last year, uh, where we had to fix some bugs. "
            "It was like, kind of hard because, um, I wasn't sure exactly what was causing "
            "the issue. I think maybe it was a database problem, but I'm not totally sure. "
            "We, uh, eventually fixed it, I guess, after a few days of, you know, debugging."
        ),
        "duration_seconds": 35.0,
        "question_id": "Q1",
        "relevance_score": 0.6,
        "is_vague": True,
    },
    {
        "candidate_id": "inexperienced_fresher",
        "role_level": RoleLevel.fresher,
        "answer_text": (
            "I worked on a college project. We made a small app. It was fun. "
            "I learned some coding basics."
        ),
        "duration_seconds": 10.0,
        "question_id": "Q1",
        "relevance_score": 0.5,
        "is_vague": True,
    },
    {
        "candidate_id": "overqualified_senior",
        "role_level": RoleLevel.senior,
        "answer_text": (
            "Throughout my fifteen years in distributed systems engineering, I have "
            "architected large-scale event-driven platforms handling millions of "
            "transactions per second. I led the redesign of our consensus layer using a "
            "Raft-based protocol, therefore improving fault tolerance significantly. I also "
            "mentored several engineering teams on distributed tracing and observability "
            "best practices. However, I sometimes found the current role's scope narrower "
            "than my prior responsibilities. I believe my depth of experience in system "
            "architecture, performance tuning, and technical leadership would translate "
            "well here."
        ),
        "duration_seconds": 45.0,
        "question_id": "Q1",
        "relevance_score": 0.85,
        # contradiction_detected is derived downstream from the answer text itself
        # (via analyze_behavior's contrast-marker check); is_vague is authored here
        # because this profile's answer is deliberately NOT vague.
        "is_vague": False,
    },
]


# ---------------------------------------------------------------------------
# Authored expectations (OUR design intent, NOT human-evaluator ground truth)
# ---------------------------------------------------------------------------

EXPECTED_OUTCOME: dict[str, dict[str, str]] = {
    "confident_senior": {
        "expected_decision": "Strong Hire",
        "rationale": (
            "confident_senior: long, structured, low-hesitation, no-uncertainty answer "
            "with an ideal-pace delivery should score Strong Hire under current weighting."
        ),
    },
    "hesitant_mid": {
        "expected_decision": "Consider",
        "rationale": (
            "hesitant_mid: moderate-length answer with several filler words and explicit "
            "uncertainty phrases should be pulled down from Strong Hire but not collapse "
            "to Reject, landing in the Consider band."
        ),
    },
    "inexperienced_fresher": {
        "expected_decision": "Consider",
        "rationale": (
            "inexperienced_fresher: short, simple, low-structure but not contradictory or "
            "hostile answer; fresher-level weighting favors communication, so a short but "
            "clean answer should land in Consider rather than Reject."
        ),
    },
    "overqualified_senior": {
        "expected_decision": "Consider",
        "rationale": (
            "overqualified_senior: technically dense and structured, but the single "
            "contrast marker trips contradiction_detected, dropping the consistency "
            "sub-score to 0.3 and pulling the outcome down from Strong Hire to Consider."
        ),
    },
}


# ---------------------------------------------------------------------------
# Pipeline runner
# ---------------------------------------------------------------------------


def run_profile(profile: CandidateProfile) -> dict:
    """Run one candidate profile through the real Day 35-39 pipeline.

    Args:
        profile: A fixed synthetic candidate profile.

    Returns:
        A dict of computed results plus the authored expectation and a
        MATCH/MISMATCH comparison, for reporting.
    """
    candidate_id = profile["candidate_id"]
    text = profile["answer_text"]
    duration = profile["duration_seconds"]
    role_level = profile["role_level"]

    logger.info("Running profile: %s", candidate_id)

    communication: CommunicationScore = calculate_communication_score(text)
    behavior: ConfidenceBehaviorScore = analyze_behavior(text, duration)

    answer_dict = {
        "question_id": profile["question_id"],
        "relevance_score": profile["relevance_score"],
        "communication_score": communication.communication_score / 100.0,
        "confidence_score": behavior.confidence.confidence_score / 100.0,
        "contradiction_detected": behavior.behavior_flags.contradiction_detected,
        "is_vague": profile["is_vague"],
    }

    hr_result: HRInterviewScore = hr_scoring_pipeline([answer_dict], role_level)

    summary = generate_interview_summary(
        candidate_id=candidate_id,
        hr_result=hr_result,
        communication=communication,
        behavior=behavior,
    )

    actual_decision = summary.composite.decision
    expected = EXPECTED_OUTCOME[candidate_id]
    expected_decision = expected["expected_decision"]
    match = actual_decision == expected_decision

    return {
        "candidate_id": candidate_id,
        "role_level": role_level.value,
        "communication_score": communication.communication_score,
        "confidence_score": behavior.confidence.confidence_score,
        "behavioral_score": behavior.behavioral_score,
        "contradiction_detected": behavior.behavior_flags.contradiction_detected,
        "hr_score": hr_result.hr_score,
        "hr_decision": hr_result.decision,
        "overall_score": summary.composite.overall_score,
        "actual_decision": actual_decision,
        "expected_decision": expected_decision,
        "rationale": expected["rationale"],
        "match": match,
        "natural_language_summary": summary.natural_language_summary,
    }


def print_profile_report(result: dict) -> None:
    """Print the full per-profile report block."""
    print("-" * 78)
    print(f"Candidate:            {result['candidate_id']} (role_level={result['role_level']})")
    print(f"Communication score:  {result['communication_score']:.2f}")
    print(f"Confidence score:     {result['confidence_score']:.2f}")
    print(f"Behavioral score:     {result['behavioral_score']:.2f}")
    print(f"Contradiction flag:   {result['contradiction_detected']}")
    print(f"HR score:             {result['hr_score']:.2f} ({result['hr_decision']})")
    print(f"Composite overall:    {result['overall_score']:.2f}")
    print(f"ACTUAL decision:      {result['actual_decision']}")
    print(f"EXPECTED decision:    {result['expected_decision']}  (authored design intent)")
    print(f"Rationale:            {result['rationale']}")
    print(f"Result:               {'MATCH' if result['match'] else 'MISMATCH'}")
    print(f"Summary narrative:    {result['natural_language_summary']}")


def print_summary_table(results: list[dict]) -> None:
    """Print the final summary table across all 4 profiles."""
    print("=" * 78)
    print("SUMMARY TABLE")
    print(f"{'candidate_id':<24}{'actual':<16}{'expected':<16}{'match'}")
    matched = 0
    for r in results:
        if r["match"]:
            matched += 1
        print(f"{r['candidate_id']:<24}{r['actual_decision']:<16}{r['expected_decision']:<16}{r['match']}")
    print("-" * 78)
    print(f"{matched} of {len(results)} profiles matched expected outcome.")
    print(
        "NOTE: 'expected' above is our own authored design intent for this "
        "simulation, not real human-evaluator ground truth. No accuracy claim "
        "against real human judgment is made or computable from this data."
    )


def main() -> None:
    """Run all 4 profiles through the real pipeline and print the full report."""
    print("=" * 78)
    print("DAY 40 — HR INTERVIEW SIMULATION (calibration / sanity check only)")
    print(
        "Expected outcomes below are authored design intent, NOT real "
        "human-evaluator ground truth. No random module is used anywhere."
    )
    print("=" * 78)

    results = [run_profile(profile) for profile in PROFILES]

    for result in results:
        print_profile_report(result)

    print_summary_table(results)


if __name__ == "__main__":
    main()
