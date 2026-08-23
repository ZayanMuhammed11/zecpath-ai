"""
tests/simulate_demo_dataset_day63.py

Demo-dataset script for Zecpath AI — Sprint 3, Day 63.

This script exercises the full 9-module hiring pipeline end-to-end
(ATS -> HR interview -> technical_ai -> machine_test_ai ->
visual_behavior_ai -> integrity_ai -> decision_ai -> final_decision_ai ->
hiring_report_ai) on THREE fixed, hand-authored QE-sector candidate
profiles, representing three quality tiers for demo purposes:

    1. strong_automotive_candidate    — automotive_quality, senior tier,
       genuinely strong across every stage.
    2. average_food_safety_candidate  — food_safety_systems, mid tier,
       solidly average across every stage, no risk flags.
    3. weak_pharma_candidate          — pharmaceutical_quality, fresher
       tier, genuinely weak across every stage.

All three candidates run the FULL 9-module chain with ALL 5 rounds present
(ats, screening, hr, technical, machine_test) — no round is deliberately
omitted for any of these three. (The Day 56 script already exercises the
machine_test-omission structural case; that is not repeated here.)

This is a demo/calibration script built on top of the already-tested Day 56
pipeline wiring (see tests/simulate_full_system_day56.py). The three
JobProfile builder functions and their _JOB_PROFILE_BUILDERS dict below are
copied VERBATIM from that file, per DAY63_DECISIONS.md — their content,
weights, and thresholds are unmodified.

It is NOT a claim of production status, is NOT connected to any live API,
does NOT use real candidate data, and its results are NOT a validated claim
of real-world accuracy or AI-vs-human agreement.

SCREENING NOTE: screening_ai's pipeline is NOT invoked live in this script,
consistent with Day 56 precedent (see that script's docstring). Every
candidate's screening_score below is a FIXED, HAND-AUTHORED float chosen to
be consistent with that candidate's overall calibre — it is NOT a live
screening_ai result.

MACHINE TEST DOMAIN NOTE: machine_test_ai/machine_test_scoring.py remains
generic-track filler for pipeline-completeness purposes only, consistent
with its own module docstring's "DOMAIN-DEVIATION NOTICE" (same as Day 56).

AI VS HUMAN COMPARISON / ACCURACY: no real human-evaluator ground truth
exists for these demo profiles. This script does NOT compute or print any
"AI vs human accuracy", "match rate", or "score correlation" percentage.

PERFORMANCE / TIMING: not measured.

This is NOT a pytest file — it is a manual demonstration script, deliberately
excluded from the pytest suite. Run it manually with:

    python -m tests.simulate_demo_dataset_day63

No random module is used anywhere in this script; all demo data below is
fixed and hand-authored. See DAY63_DECISIONS.md for the full rationale
behind this script's JSON-output field choices and any deviations from the
attached Day 56 pattern.
"""

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

# ─── ats_engine / utils.schemas ────────────────────────────────────────────
from scoring.ats_scorer import ATSScorer
from utils.schemas import (
    CandidateProfile,
    CertificationObject,
    CompanyType,
    EducationObject,
    EmploymentType,
    ExperienceObject,
    GradeType,
    JobProfile,
    ParsingMetadata,
    ScoringWeights,
    SkillLevel,
    SkillObject,
)

# ─── interview_ai (HR interview: communication / behavior / hr / summary) ──
from interview_ai.behavior_analyzer import analyze_behavior
from interview_ai.communication_engine import calculate_communication_score
from interview_ai.communication_models import CommunicationScore
from interview_ai.confidence_models import ConfidenceBehaviorScore
from interview_ai.hr_scoring_engine import hr_scoring_pipeline
from interview_ai.hr_scoring_models import HRInterviewScore
from interview_ai.interview_models import RoleLevel as InterviewRoleLevel
from interview_ai.summary_generator import generate_interview_summary

# ─── technical_ai ───────────────────────────────────────────────────────────
from technical_ai.technical_scoring_engine import technical_scoring_pipeline
from technical_ai.technical_scoring_models import TechnicalInterviewScore

# ─── machine_test_ai ────────────────────────────────────────────────────────
from machine_test_ai.machine_test_scoring import calculate_machine_test_score
from machine_test_ai.machine_test_models import MachineTestScore

# ─── visual_behavior_ai ─────────────────────────────────────────────────────
from visual_behavior_ai.visual_behavior_scoring import (
    calculate_visual_behavior_score,
)
from visual_behavior_ai.visual_behavior_models import VisualBehaviorScore

# ─── integrity_ai ───────────────────────────────────────────────────────────
from integrity_ai.integrity_scoring import calculate_integrity_score
from integrity_ai.integrity_models import IntegrityScore

# ─── decision_ai (5-round unified scoring) ─────────────────────────────────
from decision_ai.decision_models import RoleLevel as DecisionRoleLevel, RoundScores
from decision_ai.unified_scoring_engine import unified_scoring_pipeline

# ─── final_decision_ai ──────────────────────────────────────────────────────
from final_decision_ai.final_decision_engine import final_decision_pipeline

# ─── hiring_report_ai ───────────────────────────────────────────────────────
from hiring_report_ai.hiring_report_engine import build_hiring_report

from utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Shared parsing metadata (fixed, hand-authored — not a live parse)
#
# Copied verbatim from tests/simulate_full_system_day56.py — see
# DAY63_DECISIONS.md.
# ---------------------------------------------------------------------------


def _demo_parsing_metadata(confidence_score: float = 95.0) -> ParsingMetadata:
    """Build a fixed, hand-authored ParsingMetadata for demo profiles.

    This script does not run a live resume/JD parser — candidate and job
    profiles are hand-authored directly as schema objects — so this
    metadata is a fixed placeholder, not the output of a real parse.

    Args:
        confidence_score: Placeholder confidence value (0-100).

    Returns:
        A populated ParsingMetadata instance.
    """
    return ParsingMetadata(
        model_used="hand-authored-demo-fixture",
        parsed_at=datetime.now(timezone.utc).isoformat(),
        confidence_score=confidence_score,
        parsing_version="day56-demo-v1",
    )


# ---------------------------------------------------------------------------
# Job profiles (one per skill_domain)
#
# Copied VERBATIM from tests/simulate_full_system_day56.py, including the
# _JOB_PROFILE_BUILDERS dict — content, weights, and thresholds unmodified.
# See DAY63_DECISIONS.md.
# ---------------------------------------------------------------------------


def build_automotive_job_profile() -> JobProfile:
    """Build the automotive_quality QE job profile.

    REAL, CALIBRATED DATA: must_have_skills, required_skills, and
    shortlist_threshold reuse the project's own previously-calibrated
    Day 18/Day 23 automotive values, per SYSTEM_STATE_LOG — these are not
    newly invented for this script. See DAY56_DECISIONS.md.

    Returns:
        A populated JobProfile for an automotive_quality Quality Engineer
        role.
    """
    required_skills = [
        SkillObject(name="FMEA", level=SkillLevel.advanced, years_of_experience=3.0, is_primary_skill=True),
        SkillObject(name="Control Plans", level=SkillLevel.advanced, years_of_experience=3.0, is_primary_skill=True),
        SkillObject(name="SPC", level=SkillLevel.advanced, years_of_experience=3.0, is_primary_skill=True),
        SkillObject(name="PPAP", level=SkillLevel.advanced, years_of_experience=3.0, is_primary_skill=True),
        SkillObject(name="APQP", level=SkillLevel.advanced, years_of_experience=3.0, is_primary_skill=True),
        SkillObject(name="CAPA", level=SkillLevel.intermediate, years_of_experience=2.0, is_primary_skill=False),
        SkillObject(name="8D", level=SkillLevel.intermediate, years_of_experience=2.0, is_primary_skill=False),
        SkillObject(name="RCA", level=SkillLevel.intermediate, years_of_experience=2.0, is_primary_skill=False),
        SkillObject(name="IATF 16949", level=SkillLevel.advanced, years_of_experience=3.0, is_primary_skill=True),
    ]

    return JobProfile(
        job_id="JOB-AUTO-QE-001",
        title="Quality Engineer",
        department="Quality Assurance",
        company_name="Zecpath Automotive Client",
        company_type=CompanyType.mnc,
        location="Pune, Maharashtra",
        employment_type=EmploymentType.fulltime,
        salary_min_inr=600000,
        salary_max_inr=1400000,
        required_skills=required_skills,
        preferred_skills=[],
        must_have_skills=["FMEA", "Control Plans", "SPC", "PPAP", "APQP"],
        required_education_level="bachelors",
        required_education_field=[
            "mechanical engineering",
            "industrial engineering",
            "production engineering",
        ],
        responsibilities=[
            "Lead FMEA and control plan development for new automotive programs.",
            "Drive SPC-based process monitoring on the shop floor.",
            "Own PPAP submissions and APQP milestones with suppliers.",
        ],
        nice_to_have=["Six Sigma Black Belt", "ASQ CQE"],
        shortlist_threshold=40.0,
        scoring_weights=ScoringWeights(skills=40, experience=30, education=20, location=10),
        jd_raw_text=(
            "We are hiring a Quality Engineer for our automotive components "
            "plant. The role owns FMEA, control plans, SPC, PPAP, and APQP "
            "activities across new product introduction, working closely "
            "with suppliers on IATF 16949 compliance, CAPA, 8D, and root "
            "cause analysis for field and line issues."
        ),
        parsing_metadata=_demo_parsing_metadata(),
    )


def build_food_safety_job_profile() -> JobProfile:
    """Build the food_safety_systems QE job profile.

    NEWLY AUTHORED DATA: no prior real calibrated job profile exists for
    this sector on this platform. required_skills/must_have_skills are
    authored for this script from technical_ai's real Day 46 sector
    content (HACCP/GMP/SQF/ISO 22000/FSSC 22000), not independently
    calibrated. See DAY56_DECISIONS.md.

    Returns:
        A populated JobProfile for a food_safety_systems Quality Engineer
        role.
    """
    required_skills = [
        SkillObject(name="HACCP", level=SkillLevel.advanced, years_of_experience=2.0, is_primary_skill=True),
        SkillObject(name="GMP", level=SkillLevel.advanced, years_of_experience=2.0, is_primary_skill=True),
        SkillObject(name="SQF", level=SkillLevel.intermediate, years_of_experience=1.0, is_primary_skill=True),
        SkillObject(name="ISO 22000", level=SkillLevel.intermediate, years_of_experience=1.0, is_primary_skill=False),
        SkillObject(name="FSSC 22000", level=SkillLevel.intermediate, years_of_experience=1.0, is_primary_skill=False),
    ]

    return JobProfile(
        job_id="JOB-FOOD-QE-002",
        title="Quality Engineer",
        department="Quality Assurance",
        company_name="Zecpath Food Safety Client",
        company_type=CompanyType.mnc,
        location="Anand, Gujarat",
        employment_type=EmploymentType.fulltime,
        salary_min_inr=500000,
        salary_max_inr=1000000,
        required_skills=required_skills,
        preferred_skills=[],
        must_have_skills=["HACCP", "GMP", "SQF"],
        required_education_level="bachelors",
        required_education_field=[
            "food technology",
            "food science",
            "dairy technology",
        ],
        responsibilities=[
            "Maintain HACCP plans and GMP compliance across production lines.",
            "Support SQF and ISO 22000 / FSSC 22000 certification audits.",
        ],
        nice_to_have=["FSSAI certification", "BRC"],
        shortlist_threshold=45.0,
        scoring_weights=ScoringWeights(skills=40, experience=30, education=20, location=10),
        jd_raw_text=(
            "We are hiring a Quality Engineer for our dairy and food "
            "processing facility. The role maintains HACCP plans, GMP "
            "compliance, and supports SQF, ISO 22000, and FSSC 22000 "
            "certification audits across production lines."
        ),
        parsing_metadata=_demo_parsing_metadata(),
    )


def build_pharma_job_profile() -> JobProfile:
    """Build the pharmaceutical_quality QE job profile.

    NEWLY AUTHORED DATA: no prior real calibrated job profile exists for
    this sector on this platform. required_skills/must_have_skills are
    authored for this script from technical_ai's real Day 46 sector
    content (21 CFR Part 211, IQ-OQ-PQ, CAPA, GMP Pharmaceutical), not
    independently calibrated. See DAY56_DECISIONS.md.

    Returns:
        A populated JobProfile for a pharmaceutical_quality Quality
        Engineer role.
    """
    required_skills = [
        SkillObject(name="GMP Pharmaceutical", level=SkillLevel.intermediate, years_of_experience=1.0, is_primary_skill=True),
        SkillObject(name="CAPA", level=SkillLevel.intermediate, years_of_experience=1.0, is_primary_skill=True),
        SkillObject(name="21 CFR Part 211", level=SkillLevel.beginner, years_of_experience=0.5, is_primary_skill=False),
        SkillObject(name="IQ-OQ-PQ", level=SkillLevel.beginner, years_of_experience=0.5, is_primary_skill=False),
        SkillObject(name="GxP", level=SkillLevel.beginner, years_of_experience=0.5, is_primary_skill=False),
    ]

    return JobProfile(
        job_id="JOB-PHARMA-QE-003",
        title="Quality Engineer",
        department="Quality Assurance",
        company_name="Zecpath Pharmaceutical Client",
        company_type=CompanyType.mnc,
        location="Hyderabad, Telangana",
        employment_type=EmploymentType.fulltime,
        salary_min_inr=350000,
        salary_max_inr=700000,
        required_skills=required_skills,
        preferred_skills=[],
        must_have_skills=["GMP Pharmaceutical", "CAPA"],
        required_education_level="bachelors",
        required_education_field=["pharmacy", "pharmaceutical sciences"],
        responsibilities=[
            "Support GMP Pharmaceutical compliance and CAPA closure.",
            "Assist with IQ-OQ-PQ validation documentation and 21 CFR Part 211 readiness.",
        ],
        nice_to_have=["ICH guidelines exposure"],
        shortlist_threshold=35.0,
        scoring_weights=ScoringWeights(skills=40, experience=30, education=20, location=10),
        jd_raw_text=(
            "We are hiring an entry-level Quality Engineer for our "
            "pharmaceutical manufacturing site. The role supports GMP "
            "Pharmaceutical compliance, CAPA closure, IQ-OQ-PQ validation "
            "documentation, and readiness for 21 CFR Part 211 audits."
        ),
        parsing_metadata=_demo_parsing_metadata(),
    )


_JOB_PROFILE_BUILDERS = {
    "automotive_quality": build_automotive_job_profile,
    "food_safety_systems": build_food_safety_job_profile,
    "pharmaceutical_quality": build_pharma_job_profile,
}


# ---------------------------------------------------------------------------
# Demo candidate profiles — Day 63 dataset (NEW content, independently
# authored per candidate; see DAY63_DECISIONS.md)
# ---------------------------------------------------------------------------


def build_demo_profiles() -> List[Dict[str, Any]]:
    """Build the fixed set of hand-authored Day 63 demo candidate profiles.

    Three profiles are defined, one per quality tier:
        1. strong_automotive_candidate   — senior, automotive_quality, full
           5 rounds, genuinely strong across every stage.
        2. average_food_safety_candidate — mid, food_safety_systems, full 5
           rounds, solidly average across every stage, no risk flags.
        3. weak_pharma_candidate         — fresher, pharmaceutical_quality,
           full 5 rounds, genuinely weak across every stage.

    No random module is used — every value below is fixed and authored by
    hand for calibration/demonstration purposes only. Unlike Day 56's
    mid_partial_qe_journey, none of these three candidates omits any round.

    Returns:
        A list of profile dicts, each fully self-describing for every
        pipeline stage (see per-key comments inline).
    """
    return [
        # =====================================================================
        # 1. strong_automotive_candidate — automotive_quality, senior,
        #    genuinely strong across every stage, full 5 rounds
        # =====================================================================
        {
            "candidate_id": "strong_automotive_candidate",
            "skill_domain": "automotive_quality",
            "role_level": InterviewRoleLevel.senior,
            "job_title_display": "Senior Quality Engineer — Automotive (Demo)",
            "candidate_profile_kwargs": dict(
                candidate_id="strong_automotive_candidate",
                full_name="Vikram Nair",
                email="vikram.nair@example.com",
                phone="+91-9000001001",
                location="Pune, Maharashtra",
                is_actively_looking=True,
                skills=[
                    SkillObject(name="FMEA", level=SkillLevel.expert, years_of_experience=9.0, is_primary_skill=True),
                    SkillObject(name="Control Plans", level=SkillLevel.expert, years_of_experience=8.0, is_primary_skill=True),
                    SkillObject(name="SPC", level=SkillLevel.advanced, years_of_experience=9.0, is_primary_skill=True),
                    SkillObject(name="PPAP", level=SkillLevel.expert, years_of_experience=8.0, is_primary_skill=True),
                    SkillObject(name="APQP", level=SkillLevel.advanced, years_of_experience=7.0, is_primary_skill=True),
                    SkillObject(name="CAPA", level=SkillLevel.advanced, years_of_experience=6.0, is_primary_skill=False),
                    SkillObject(name="8D", level=SkillLevel.advanced, years_of_experience=7.0, is_primary_skill=False),
                    SkillObject(name="RCA", level=SkillLevel.advanced, years_of_experience=7.0, is_primary_skill=False),
                    SkillObject(name="IATF 16949", level=SkillLevel.expert, years_of_experience=8.0, is_primary_skill=True),
                ],
                experience=[
                    ExperienceObject(
                        company_name="Mahindra Auto Systems Ltd",
                        role_title="Senior Quality Engineer",
                        department="Quality Assurance",
                        company_type=CompanyType.mnc,
                        location="Pune, Maharashtra",
                        employment_type=EmploymentType.fulltime,
                        start_date="2020-02",
                        end_date=None,
                        is_current=True,
                        duration_months=54,
                        responsibilities=[
                            "Own FMEA and control plan strategy across three vehicle programs.",
                            "Lead PPAP and APQP governance with tier-1 suppliers.",
                        ],
                        technologies_used=["FMEA", "PPAP", "APQP", "SPC", "IATF 16949"],
                        achievements=["Cut supplier PPAP rejection rate by 38% over two years."],
                    ),
                    ExperienceObject(
                        company_name="Bosch Auto Parts",
                        role_title="Quality Engineer",
                        department="Quality",
                        company_type=CompanyType.mnc,
                        location="Bangalore, Karnataka",
                        employment_type=EmploymentType.fulltime,
                        start_date="2015-06",
                        end_date="2020-01",
                        is_current=False,
                        duration_months=56,
                        responsibilities=["Ran SPC monitoring on production lines.", "Led 8D/RCA investigations."],
                        technologies_used=["SPC", "8D", "RCA"],
                        achievements=["Closed 50+ CAPAs with zero repeat findings."],
                    ),
                ],
                education=[
                    EducationObject(
                        degree="B.Tech",
                        field_of_study="Mechanical Engineering",
                        institution_name="VJTI Mumbai",
                        location="Mumbai, Maharashtra",
                        start_year=2007,
                        end_year=2011,
                        grade="8.6",
                        grade_type=GradeType.cgpa,
                        is_highest_qualification=True,
                    ),
                ],
                certifications=[
                    CertificationObject(
                        name="Six Sigma Black Belt",
                        issuing_organization="ASQ",
                        issue_date="2014-09",
                        expiry_date=None,
                        credential_id="ASQ-SSBB-9001",
                        is_expired=False,
                    ),
                    CertificationObject(
                        name="ASQ CQE",
                        issuing_organization="ASQ",
                        issue_date="2015-11",
                        expiry_date=None,
                        credential_id="ASQ-CQE-9002",
                        is_expired=False,
                    ),
                    CertificationObject(
                        name="IATF 16949 Lead Auditor",
                        issuing_organization="TUV SUD",
                        issue_date="2017-04",
                        expiry_date=None,
                        credential_id="TUV-IATF-9003",
                        is_expired=False,
                    ),
                ],
                languages_known=["English", "Hindi", "Marathi"],
                expected_salary_inr=1350000,
                notice_period_days=60,
                raw_text=None,
                parsing_metadata=_demo_parsing_metadata(),
            ),
            "segmented_resume": {
                "sections": [
                    {
                        "section": "skills",
                        "content": (
                            "FMEA, Control Plans, SPC, PPAP, APQP, CAPA, 8D, RCA, "
                            "IATF 16949, Six Sigma Black Belt, supplier quality governance."
                        ),
                    },
                    {
                        "section": "experience",
                        "content": (
                            "Senior Quality Engineer owning FMEA and control plan "
                            "strategy across multiple vehicle programs, leading PPAP "
                            "and APQP governance with tier-1 suppliers, running "
                            "SPC-based monitoring, and closing CAPAs via 8D and root "
                            "cause analysis for IATF 16949 compliance."
                        ),
                    },
                ]
            },
            "screening_score": 88.0,  # fixed, hand-authored — see module docstring
            "hr_answer": {
                "question_id": "Q1",
                "answer_text": (
                    "In my current role I led the FMEA and control plan overhaul "
                    "for a new steering-column program after early validation "
                    "builds showed an unacceptable defect trend. First, I pulled "
                    "the FMEA severity and occurrence ratings and traced the "
                    "highest-risk failure mode to an under-specified tolerance in "
                    "the control plan. Then, I revised the control plan, tightened "
                    "the SPC limits on the critical dimension, and re-ran the "
                    "process capability study. As a result, the defect rate "
                    "dropped by more than 60% within one quarter and stayed there "
                    "through launch. I coordinated the PPAP resubmission with the "
                    "supplier and kept the APQP timeline intact. Because IATF "
                    "16949 compliance mattered for the program milestone review, I "
                    "documented every change through CAPA and ran a joint 8D with "
                    "the supplier's quality team. Finally, I trained the line "
                    "inspectors on the revised control plan so the gains would "
                    "hold after I handed the program off."
                ),
                "duration_seconds": 48.0,
                "relevance_score": 0.95,
                "is_vague": False,
            },
            "technical_answers": [
                {
                    "question_id": "T1",
                    "phase": "experience_based",
                    "accuracy": 0.94,
                    "text": (
                        "On the production line, we had a recurring dimensional "
                        "deviation. First I ran a root cause analysis, pulling the "
                        "SPC charts and the control plan together. Because the "
                        "tolerance was tight, small tool wear had a real impact. "
                        "Therefore we added a control point and, as a result, "
                        "deviations dropped sharply. In practice this is a "
                        "trade-off between inspection frequency and cycle time, "
                        "which we validated during a supplier audit."
                    ),
                },
                {
                    "question_id": "T2",
                    "phase": "scenario_based",
                    "accuracy": 0.91,
                    "text": (
                        "If a supplier's PPAP submission shows a marginal "
                        "capability index, I would first review the control plan "
                        "and specification together, then request updated process "
                        "data. This matters because the risk of field failure "
                        "increases with any tolerance drift, so in our facility we "
                        "would hold the part on a deviation until root cause is "
                        "confirmed."
                    ),
                },
                {
                    "question_id": "T3",
                    "phase": "conceptual",
                    "accuracy": 0.93,
                    "text": (
                        "APQP exists so that risk is managed before mass "
                        "production, which means FMEA, control plans, and PPAP "
                        "are all linked. Because of this, a specification change "
                        "late in the program has a large impact on timeline and "
                        "cost, which we saw for example during a real-world "
                        "program launch where a late tolerance change forced a "
                        "full PPAP resubmission."
                    ),
                },
            ],
            "machine_test_submission": {
                "passed_test_count": 10,
                "total_test_count": 10,
                "runtime_seconds": 1.5,
                "runtime_baseline_seconds": 2.0,
                "code_quality": 0.9,
                "attempts": 1,
                "time_taken_seconds": 780.0,
                "time_limit_seconds": 1200.0,
            },
            "visual_behavior_signals": {
                "gaze_stability": 0.91,
                "head_stability": 0.89,
                "facial_engagement": 0.87,
                "attention_consistency": 0.9,
            },
            "integrity_events": {
                "tab_switch_count": 0,
                "focus_loss_count": 0,
                "external_voice_count": 0,
                "gaze_deviation_count": 0,
            },
        },
        # =====================================================================
        # 2. average_food_safety_candidate — food_safety_systems, mid,
        #    solidly average across every stage, no risk flags, full 5 rounds
        # =====================================================================
        {
            "candidate_id": "average_food_safety_candidate",
            "skill_domain": "food_safety_systems",
            "role_level": InterviewRoleLevel.mid,
            "job_title_display": "Quality Engineer — Food Safety Systems (Demo)",
            "candidate_profile_kwargs": dict(
                candidate_id="average_food_safety_candidate",
                full_name="Priya Deshmukh",
                email="priya.deshmukh@example.com",
                phone="+91-9000002002",
                location="Anand, Gujarat",
                is_actively_looking=True,
                skills=[
                    SkillObject(name="HACCP", level=SkillLevel.intermediate, years_of_experience=3.0, is_primary_skill=True),
                    SkillObject(name="GMP", level=SkillLevel.intermediate, years_of_experience=3.0, is_primary_skill=True),
                    SkillObject(name="SQF", level=SkillLevel.intermediate, years_of_experience=2.0, is_primary_skill=True),
                    SkillObject(name="ISO 22000", level=SkillLevel.beginner, years_of_experience=1.5, is_primary_skill=False),
                    SkillObject(name="FSSC 22000", level=SkillLevel.beginner, years_of_experience=1.0, is_primary_skill=False),
                    SkillObject(name="CAPA", level=SkillLevel.intermediate, years_of_experience=2.0, is_primary_skill=False),
                ],
                experience=[
                    ExperienceObject(
                        company_name="Amul Dairy Processing Unit",
                        role_title="Quality Engineer",
                        department="Quality Assurance",
                        company_type=CompanyType.mnc,
                        location="Anand, Gujarat",
                        employment_type=EmploymentType.fulltime,
                        start_date="2021-08",
                        end_date=None,
                        is_current=True,
                        duration_months=36,
                        responsibilities=[
                            "Monitor HACCP critical control points across one production line.",
                            "Support SQF and ISO 22000 audit preparation.",
                        ],
                        technologies_used=["HACCP", "GMP", "SQF"],
                        achievements=["Maintained zero critical findings across two SQF surveillance audits."],
                    ),
                ],
                education=[
                    EducationObject(
                        degree="B.Tech",
                        field_of_study="Food Technology",
                        institution_name="Gujarat Technological University",
                        location="Ahmedabad, Gujarat",
                        start_year=2016,
                        end_year=2020,
                        grade="7.1",
                        grade_type=GradeType.cgpa,
                        is_highest_qualification=True,
                    ),
                ],
                certifications=[
                    CertificationObject(
                        name="HACCP",
                        issuing_organization="Codex Alimentarius",
                        issue_date="2021-01",
                        expiry_date=None,
                        credential_id="CA-HACCP-5001",
                        is_expired=False,
                    ),
                ],
                languages_known=["English", "Hindi", "Gujarati"],
                expected_salary_inr=750000,
                notice_period_days=30,
                raw_text=None,
                parsing_metadata=_demo_parsing_metadata(),
            ),
            "segmented_resume": {
                "sections": [
                    {
                        "section": "skills",
                        "content": "HACCP, GMP, SQF, ISO 22000 basics, FSSC 22000 basics, CAPA.",
                    },
                    {
                        "section": "experience",
                        "content": (
                            "Quality Engineer monitoring HACCP critical control "
                            "points on a dairy production line and supporting SQF "
                            "and ISO 22000 audit preparation."
                        ),
                    },
                ]
            },
            "screening_score": 62.0,  # fixed, hand-authored — see module docstring
            "hr_answer": {
                "question_id": "Q1",
                "answer_text": (
                    "In my current role I monitor the HACCP critical control "
                    "points on our pasteurization line and check the daily "
                    "temperature logs. Last quarter we had a minor deviation "
                    "during a SQF surveillance audit, so I updated the "
                    "monitoring checklist and walked the line staff through the "
                    "correction. I usually start my shift by reviewing overnight "
                    "logs before anything else."
                ),
                "duration_seconds": 24.0,
                "relevance_score": 0.68,
                "is_vague": False,
            },
            "technical_answers": [
                {
                    "question_id": "T1",
                    "phase": "experience_based",
                    "accuracy": 0.64,
                    "text": (
                        "We had a temperature logging gap on the pasteurization "
                        "line. First we reviewed the HACCP plan, then updated the "
                        "monitoring checklist. Because product safety was at "
                        "stake, we also retrained staff on correct logging."
                    ),
                },
                {
                    "question_id": "T2",
                    "phase": "conceptual",
                    "accuracy": 0.6,
                    "text": (
                        "GMP covers general hygiene practices while HACCP "
                        "identifies the specific risk points on the line, and "
                        "both are checked during an SQF audit."
                    ),
                },
            ],
            "machine_test_submission": {
                "passed_test_count": 6,
                "total_test_count": 10,
                "runtime_seconds": 2.4,
                "runtime_baseline_seconds": 2.0,
                "code_quality": 0.6,
                "attempts": 3,
                "time_taken_seconds": 1050.0,
                "time_limit_seconds": 1200.0,
            },
            "visual_behavior_signals": {
                "gaze_stability": 0.63,
                "head_stability": 0.65,
                "facial_engagement": 0.6,
                "attention_consistency": 0.62,
            },
            # Deliberately kept below the WARNING_THRESHOLDS values in
            # integrity_scoring.py (attached Day 56 script's own comment
            # documents these as tab_switch/focus_loss/external_voice/
            # gaze_deviation = 3 / 3 / 2 / 3) so this candidate produces no
            # risk flags, consistent with "solidly average" for this tier.
            "integrity_events": {
                "tab_switch_count": 1,
                "focus_loss_count": 1,
                "external_voice_count": 0,
                "gaze_deviation_count": 1,
            },
        },
        # =====================================================================
        # 3. weak_pharma_candidate — pharmaceutical_quality, fresher,
        #    genuinely weak across every stage, full 5 rounds
        # =====================================================================
        {
            "candidate_id": "weak_pharma_candidate",
            "skill_domain": "pharmaceutical_quality",
            "role_level": InterviewRoleLevel.fresher,
            "job_title_display": "Quality Engineer — Pharmaceutical (Entry Level, Demo)",
            "candidate_profile_kwargs": dict(
                candidate_id="weak_pharma_candidate",
                full_name="Arjun Kulkarni",
                email="arjun.kulkarni@example.com",
                phone="+91-9000003003",
                location="Hyderabad, Telangana",
                is_actively_looking=True,
                skills=[
                    SkillObject(name="GMP Pharmaceutical", level=SkillLevel.beginner, years_of_experience=0.3, is_primary_skill=True),
                    SkillObject(name="CAPA", level=SkillLevel.beginner, years_of_experience=0.3, is_primary_skill=False),
                ],
                experience=[
                    ExperienceObject(
                        company_name="MediGen Pharma Pvt Ltd",
                        role_title="Quality Trainee",
                        department="Quality",
                        company_type=CompanyType.mnc,
                        location="Hyderabad, Telangana",
                        employment_type=EmploymentType.internship,
                        start_date="2024-07",
                        end_date="2024-12",
                        is_current=False,
                        duration_months=5,
                        responsibilities=["Filed batch documentation."],
                        technologies_used=["GMP Pharmaceutical"],
                        achievements=[],
                    ),
                ],
                education=[
                    EducationObject(
                        degree="B.Pharma",
                        field_of_study="Pharmacy",
                        institution_name="Kakatiya University",
                        location="Warangal, Telangana",
                        start_year=2020,
                        end_year=2024,
                        grade="58%",
                        grade_type=GradeType.percentage,
                        is_highest_qualification=True,
                    ),
                ],
                certifications=[],
                languages_known=["English", "Telugu"],
                expected_salary_inr=280000,
                notice_period_days=15,
                raw_text=None,
                parsing_metadata=_demo_parsing_metadata(),
            ),
            "segmented_resume": {
                "sections": [
                    {
                        "section": "skills",
                        "content": "GMP Pharmaceutical basics, CAPA awareness.",
                    },
                    {
                        "section": "experience",
                        "content": (
                            "Quality trainee who filed batch documentation in a "
                            "pharmaceutical quality department."
                        ),
                    },
                ]
            },
            "screening_score": 33.0,  # fixed, hand-authored — see module docstring
            "hr_answer": {
                "question_id": "Q1",
                "answer_text": (
                    "I did a trainee stint where I filed batch documents. It "
                    "was mostly paperwork. I did not lead anything myself."
                ),
                "duration_seconds": 7.0,
                "relevance_score": 0.32,
                "is_vague": True,
            },
            "technical_answers": [
                {
                    "question_id": "T1",
                    "phase": "experience_based",
                    "accuracy": 0.28,
                    "text": "I filed batch documents and checked dates.",
                },
                {
                    "question_id": "T2",
                    "phase": "conceptual",
                    "accuracy": 0.25,
                    "text": "GMP means following the rules in the factory.",
                },
            ],
            "machine_test_submission": {
                "passed_test_count": 2,
                "total_test_count": 10,
                "runtime_seconds": 5.2,
                "runtime_baseline_seconds": 2.0,
                "code_quality": 0.3,
                "attempts": 6,
                "time_taken_seconds": 1195.0,
                "time_limit_seconds": 1200.0,
            },
            "visual_behavior_signals": {
                "gaze_stability": 0.38,
                "head_stability": 0.4,
                "facial_engagement": 0.33,
                "attention_consistency": 0.36,
            },
            "integrity_events": {
                "tab_switch_count": 1,
                "focus_loss_count": 1,
                "external_voice_count": 0,
                "gaze_deviation_count": 1,
            },
        },
    ]


# ---------------------------------------------------------------------------
# Pipeline orchestration
#
# Copied verbatim in structure/behavior from
# tests/simulate_full_system_day56.py's run_candidate_pipeline() — same
# exact call sequence and per-stage dict/field shapes, since it is generic
# over any profile dict of this shape. See DAY63_DECISIONS.md.
# ---------------------------------------------------------------------------


def run_candidate_pipeline(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Run the full 9-module hiring pipeline for one candidate profile.

    Stage order: ATS -> screening (fixed float) -> HR interview
    (communication/behavior/hr_scoring/summary) -> technical_ai ->
    machine_test_ai -> visual_behavior_ai -> integrity_ai -> decision_ai
    (5-round unified scoring) -> final_decision_ai -> hiring_report_ai.

    Args:
        profile: One demo profile dict, as produced by build_demo_profiles().

    Returns:
        A dict with keys: candidate_profile, job_profile, ats_result,
        screening_score, communication, behavior, hr_result,
        interview_summary, technical_result, machine_test_result (or None),
        visual_behavior_result, integrity_result, round_scores,
        unified_score, final_decision, hiring_report.
    """
    candidate_id: str = profile["candidate_id"]
    skill_domain: str = profile["skill_domain"]
    role_level: InterviewRoleLevel = profile["role_level"]

    logger.info("Running full system pipeline for candidate_id=%s", candidate_id)

    # ---- 1. ATS ------------------------------------------------------------
    candidate_profile = CandidateProfile(**profile["candidate_profile_kwargs"])
    job_profile = _JOB_PROFILE_BUILDERS[skill_domain]()

    ats_scorer = ATSScorer()
    ats_result: dict = ats_scorer.score(
        profile["segmented_resume"],
        candidate_profile,  # real CandidateProfile object — see DAY56_DECISIONS.md
        job_profile.model_dump(),
        job_profile.jd_raw_text or "",
    )

    # ---- 2. Screening (fixed float, NOT a live call) ------------------------
    screening_score: float = profile["screening_score"]

    # ---- 3. HR interview -----------------------------------------------------
    hr_answer = profile["hr_answer"]
    answer_text: str = hr_answer["answer_text"]
    duration_seconds: float = hr_answer["duration_seconds"]

    communication: CommunicationScore = calculate_communication_score(answer_text)
    behavior: ConfidenceBehaviorScore = analyze_behavior(answer_text, duration_seconds)

    hr_answer_dict: Dict[str, Any] = {
        "question_id": hr_answer["question_id"],
        "relevance_score": hr_answer["relevance_score"],
        "communication_score": communication.communication_score / 100.0,
        "confidence_score": behavior.confidence.confidence_score / 100.0,
        "contradiction_detected": behavior.behavior_flags.contradiction_detected,
        "is_vague": hr_answer["is_vague"],
    }
    hr_result: HRInterviewScore = hr_scoring_pipeline([hr_answer_dict], role_level=role_level)
    interview_summary = generate_interview_summary(candidate_id, hr_result, communication, behavior)

    # ---- 4. Technical --------------------------------------------------------
    technical_answer_dicts = [
        {
            "question_id": ans["question_id"],
            "skill_domain": skill_domain,
            "phase": ans["phase"],
            "accuracy": ans["accuracy"],
            "text": ans["text"],
        }
        for ans in profile["technical_answers"]
    ]
    technical_result: TechnicalInterviewScore = technical_scoring_pipeline(technical_answer_dicts)

    # ---- 5. Machine test -----------------------------------------------------
    machine_test_result: Optional[MachineTestScore] = None
    if profile["machine_test_submission"] is not None:
        machine_test_result = calculate_machine_test_score(profile["machine_test_submission"])

    # ---- 6. Visual behavior --------------------------------------------------
    visual_behavior_result: VisualBehaviorScore = calculate_visual_behavior_score(
        profile["visual_behavior_signals"]
    )

    # ---- 7. Integrity ----------------------------------------------------
    integrity_result: IntegrityScore = calculate_integrity_score(profile["integrity_events"])

    # ---- 8. decision_ai (5-round unified scoring) ---------------------------
    decision_role: DecisionRoleLevel = DecisionRoleLevel(role_level.value)
    round_scores = RoundScores(
        ats_score=ats_result["final_score"],
        screening_score=screening_score,
        hr_score=hr_result.hr_score,
        technical_score=technical_result.technical_score,
        machine_test_score=(
            machine_test_result.final_score if machine_test_result is not None else None
        ),
    )
    unified_score = unified_scoring_pipeline(candidate_id, round_scores, decision_role)

    # ---- 9. final_decision_ai ------------------------------------------------
    unified_score_dict = {
        "final_score": unified_score.final_score,
        "recommendation": unified_score.recommendation,
    }
    final_decision = final_decision_pipeline(
        candidate_id=candidate_id,
        unified_score=unified_score_dict,
        integrity_risk_level=integrity_result.risk_level,
        visual_behavior_score=visual_behavior_result.visual_behavior_score,
        visual_behavior_level=visual_behavior_result.level,
    )

    # ---- 10. hiring_report_ai ------------------------------------------------
    hr_summary_data = {
        "composite": {
            "hr_score": interview_summary.composite.hr_score,
            "decision": interview_summary.composite.decision,
        },
        "highlights": {
            "strengths": interview_summary.highlights.strengths,
            "weaknesses": interview_summary.highlights.weaknesses,
            "risks": interview_summary.highlights.risks,
            "inconsistencies": interview_summary.highlights.inconsistencies,
        },
    }
    machine_test_data = (
        {
            "final_score": machine_test_result.final_score,
            "decision": machine_test_result.decision,
        }
        if machine_test_result is not None
        else None
    )
    hiring_report = build_hiring_report(
        candidate_id=candidate_id,
        job_title=profile["job_title_display"],
        ats_data={"final_score": ats_result["final_score"], "match_label": ats_result["match_label"]},
        screening_data={"screening_score": screening_score},
        hr_summary_data=hr_summary_data,
        technical_data={"technical_score": technical_result.technical_score, "decision": technical_result.decision},
        machine_test_data=machine_test_data,
        unified_score_data=unified_score.model_dump(),
        final_decision_data=final_decision.model_dump(),
        visual_behavior_data={
            "visual_behavior_score": visual_behavior_result.visual_behavior_score,
            "level": visual_behavior_result.level,
        },
        integrity_data={
            "integrity_score": integrity_result.integrity_score,
            "risk_level": integrity_result.risk_level,
            "warnings": integrity_result.warnings,
        },
    )

    return {
        "candidate_profile": candidate_profile,
        "job_profile": job_profile,
        "ats_result": ats_result,
        "screening_score": screening_score,
        "communication": communication,
        "behavior": behavior,
        "hr_result": hr_result,
        "interview_summary": interview_summary,
        "technical_result": technical_result,
        "machine_test_result": machine_test_result,
        "visual_behavior_result": visual_behavior_result,
        "integrity_result": integrity_result,
        "round_scores": round_scores,
        "unified_score": unified_score,
        "final_decision": final_decision,
        "hiring_report": hiring_report,
    }


# ---------------------------------------------------------------------------
# Output rendering
#
# print_candidate_report() copied verbatim from
# tests/simulate_full_system_day56.py. print_summary_table() copied
# verbatim except its title text (see DAY63_DECISIONS.md).
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
    skill_domain: str = profile["skill_domain"]

    ats_result = result["ats_result"]
    hr_result: HRInterviewScore = result["hr_result"]
    interview_summary = result["interview_summary"]
    technical_result: TechnicalInterviewScore = result["technical_result"]
    machine_test_result: Optional[MachineTestScore] = result["machine_test_result"]
    visual_behavior_result: VisualBehaviorScore = result["visual_behavior_result"]
    integrity_result: IntegrityScore = result["integrity_result"]
    unified_score = result["unified_score"]
    final_decision = result["final_decision"]
    hiring_report = result["hiring_report"]

    print("=" * 78)
    print(f"CANDIDATE: {candidate_id}  (role_level={role_level.value}, domain={skill_domain})")
    print("=" * 78)

    print("\n-- 1. ATS --")
    print(f"  final_score   : {ats_result['final_score']}")
    print(f"  match_label   : {ats_result['match_label']}")
    print(f"  shortlisted   : {ats_result['shortlisted']}")
    print(f"  sub_scores    : {ats_result['sub_scores']}")

    print("\n-- 2. Screening (fixed, hand-authored — NOT a live call) --")
    print(f"  screening_score : {result['screening_score']}")

    print("\n-- 3. HR Interview --")
    print(f"  hr_score        : {hr_result.hr_score}")
    print(f"  hr_decision     : {hr_result.decision}")
    print(f"  summary         : {interview_summary.natural_language_summary}")

    print("\n-- 4. Technical --")
    print(f"  technical_score : {technical_result.technical_score}")
    print(f"  decision        : {technical_result.decision}")
    print(f"  skill_breakdown : {technical_result.skill_breakdown}")

    print("\n-- 5. Machine Test (generic SWE track — not QE-domain content) --")
    if machine_test_result is not None:
        print(f"  final_score : {machine_test_result.final_score}")
        print(f"  decision    : {machine_test_result.decision}")
    else:
        print("  ROUND NOT COMPLETED (deliberately missing for this candidate).")

    print("\n-- 6. Visual Behavior (caller-supplied placeholder signals) --")
    print(f"  visual_behavior_score : {visual_behavior_result.visual_behavior_score}")
    print(f"  level                 : {visual_behavior_result.level}")

    print("\n-- 7. Integrity (caller-supplied placeholder events) --")
    print(f"  integrity_score : {integrity_result.integrity_score}")
    print(f"  risk_level      : {integrity_result.risk_level}")
    print(f"  warnings        : {integrity_result.warnings}")

    print("\n-- 8. decision_ai: CROSS-ROUND UNIFIED SCORING --")
    print(f"  rounds_included : {unified_score.breakdown.rounds_included}")
    print(f"  rounds_missing  : {unified_score.breakdown.rounds_missing}")
    for contribution in unified_score.breakdown.contributions:
        print(
            f"    - {contribution.round_name:<12} "
            f"raw_score={contribution.raw_score:>6.2f}  "
            f"weight_used={contribution.weight_used:.4f}  "
            f"weighted_contribution={contribution.weighted_contribution:.4f}"
        )
    print(f"  final_score     : {unified_score.final_score}")
    print(f"  recommendation  : {unified_score.recommendation}")
    print(f"  confidence      : {unified_score.confidence}")
    print(
        f"  hiring_fit      : {unified_score.hiring_fit.hiring_fit_percentage}% "
        f"({unified_score.hiring_fit.fit_category})"
    )

    print("\n-- 9. final_decision_ai: RISK-ADJUSTED FINAL DECISION --")
    print(f"  base_final_score      : {final_decision.base_final_score}")
    print(f"  base_recommendation   : {final_decision.base_recommendation}")
    print(f"  risk_adjustment       : {final_decision.risk_adjustment.reason}")
    print(f"  adjusted_score        : {final_decision.adjusted_score}")
    print(f"  final_recommendation  : {final_decision.final_recommendation}")
    print(f"  decision_confidence   : {final_decision.decision_confidence}")
    if final_decision.final_recommendation != final_decision.base_recommendation:
        print(
            "  *** RECOMMENDATION CHANGED BY RISK ADJUSTMENT: "
            f"'{final_decision.base_recommendation}' -> "
            f"'{final_decision.final_recommendation}' ***"
        )

    print("\n-- 10. hiring_report_ai: AUTHORITATIVE RECOMMENDATION --")
    print(
        f"  recommendation : {hiring_report.authoritative_recommendation.recommendation} "
        f"(source: {hiring_report.authoritative_recommendation.source})"
    )
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
    print("=" * 100)
    print("SUMMARY TABLE — ALL CANDIDATES (Day 63 Demo Dataset)")
    print("=" * 100)

    header = (
        f"{'candidate_id':<30} {'base_reco':<10} {'final_reco':<10} "
        f"{'integrity_risk':<16} {'rounds_included'}"
    )
    print(header)
    print("-" * len(header))

    for profile, result in zip(profiles, results):
        unified_score = result["unified_score"]
        final_decision = result["final_decision"]
        integrity_result = result["integrity_result"]
        rounds_included_count = len(unified_score.breakdown.rounds_included)
        print(
            f"{profile['candidate_id']:<30} "
            f"{final_decision.base_recommendation:<10} "
            f"{final_decision.final_recommendation:<10} "
            f"{integrity_result.risk_level:<16} "
            f"{rounds_included_count}/5"
        )
    print()
    print(
        "NOTE: no AI-vs-human accuracy, match-rate, or score-correlation "
        "percentage is computed anywhere in this script — no ground-truth "
        "human evaluation exists for these demo profiles. Timing/latency "
        "was not measured."
    )
    print()


# ---------------------------------------------------------------------------
# JSON export (NEW for Day 63 — see DAY63_DECISIONS.md)
# ---------------------------------------------------------------------------

JSON_OUTPUT_PATH = os.path.join("data", "demo", "day63_demo_dataset.json")
INPUT_JSON_OUTPUT_PATH = os.path.join("data", "demo", "day63_demo_dataset_input.json")


def build_json_record(profile: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
    """Build one JSON-serializable record for a single candidate's run.

    Uses Pydantic's `model_dump(mode="json")` on every Pydantic-model
    result field so that any datetime/enum values inside those models are
    already converted to JSON-safe primitives (ISO strings, plain values)
    rather than raising a TypeError at json.dump() time. `ats_result` is
    already a plain dict returned by ATSScorer, so it is included as-is.

    Args:
        profile: The demo profile dict for this candidate.
        result: The dict returned by run_candidate_pipeline() for this
            candidate.

    Returns:
        A dict containing, at minimum, every field required by
        DAY63_DECISIONS.md's JSON output spec.
    """
    machine_test_result: Optional[MachineTestScore] = result["machine_test_result"]

    return {
        "candidate_id": profile["candidate_id"],
        "skill_domain": profile["skill_domain"],
        "role_level": profile["role_level"].value,
        "ats": result["ats_result"],
        "screening_score": result["screening_score"],
        "hr": result["hr_result"].model_dump(mode="json"),
        "technical": result["technical_result"].model_dump(mode="json"),
        "machine_test": (
            machine_test_result.model_dump(mode="json")
            if machine_test_result is not None
            else None
        ),
        "visual_behavior": result["visual_behavior_result"].model_dump(mode="json"),
        "integrity": result["integrity_result"].model_dump(mode="json"),
        "unified_score": result["unified_score"].model_dump(mode="json"),
        "final_decision": result["final_decision"].model_dump(mode="json"),
        "hiring_report": result["hiring_report"].model_dump(mode="json"),
    }


def save_json_output(
    profiles: List[Dict[str, Any]], results: List[Dict[str, Any]], path: str
) -> str:
    """Save the full Day 63 demo run to a JSON file.

    Creates the destination directory if it does not already exist.

    Args:
        profiles: The list of demo profile dicts, in the same order as
            `results`.
        results: The list of per-candidate result dicts returned by
            run_candidate_pipeline(), in the same order as `profiles`.
        path: Destination file path for the JSON output.

    Returns:
        The absolute path the JSON file was written to.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)

    records = [
        build_json_record(profile, result)
        for profile, result in zip(profiles, results)
    ]

    # `default=str` is a safety-net fallback only: model_dump(mode="json")
    # should already have converted every datetime/enum inside the
    # Pydantic-model fields above, and ats_result's plain dict is expected
    # to already be JSON-safe. This just guards against json.dump()
    # raising a TypeError if any stray non-JSON-serializable value slips
    # through, rather than crashing the whole run.
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, default=str)

    return os.path.abspath(path)


# ---------------------------------------------------------------------------
# INPUT JSON export (NEW for Day 63b — see DAY63B_DECISIONS.md)
#
# Persists the demo dataset's INPUT (candidate profile, job profile,
# interview answers, behavioral/integrity signals) alongside the OUTPUT
# already saved by save_json_output() above. Purely additive: does not
# touch build_demo_profiles(), run_candidate_pipeline(), the console print
# functions, build_json_record(), save_json_output(), or JSON_OUTPUT_PATH.
# ---------------------------------------------------------------------------


def _serialize_value(value: Any) -> Any:
    """Recursively convert a value into a JSON-serializable form.

    Handles, in order:
        - Pydantic BaseModel instances -> `.model_dump(mode="json")`
          (this already normalizes any nested datetime/enum fields inside
          the model to JSON-safe primitives).
        - dicts -> a new dict with the same keys, each value recursively
          serialized.
        - lists/tuples -> a new list with each item recursively
          serialized.
        - anything else (str, int, float, bool, None, and already-JSON
          values in general) -> passed through unchanged.

    This is a single generic helper rather than per-field type handling,
    so it does not need to know in advance which keys of
    `candidate_profile_kwargs` hold a plain value, a single Pydantic
    model, or a list of Pydantic models (skills, experience, education,
    certifications, parsing_metadata) — every key is handled the same way
    and none is silently dropped.

    Args:
        value: Any value that may appear inside a demo profile dict.

    Returns:
        A JSON-serializable equivalent of `value`.
    """
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {key: _serialize_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize_value(item) for item in value]
    return value


def build_input_record(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Build one JSON-serializable INPUT record for a single candidate.

    Contains exactly two top-level keys, kept deliberately unmerged:
        - "resume_and_job_data": everything that stands in for a real
          resume/JD parse — candidate identity, the candidate profile
          kwargs (skills, experience, education, certifications, parsing
          metadata), the segmented resume, and the real JobProfile for
          this candidate's skill_domain (required skills, must-haves,
          thresholds, jd_raw_text).
        - "interview_and_behavioral_signals": the caller-supplied,
          hand-authored stand-ins for live interview capture, gaze
          tracking, and code-execution infrastructure (screening score,
          HR answer, technical answers, machine-test submission, visual
          behavior signals, integrity events), explicitly labeled via a
          fixed "_note" field so a reviewer does not mistake these for
          values derived from the resume/JD data above.

    Args:
        profile: One demo profile dict, as produced by
            build_demo_profiles().

    Returns:
        A dict with exactly the two top-level keys described above.
    """
    skill_domain: str = profile["skill_domain"]
    job_profile = _JOB_PROFILE_BUILDERS[skill_domain]()

    resume_and_job_data: Dict[str, Any] = {
        "candidate_id": profile["candidate_id"],
        "skill_domain": skill_domain,
        "role_level": profile["role_level"].value,
        "job_title_display": profile["job_title_display"],
        "candidate_profile_kwargs": _serialize_value(profile["candidate_profile_kwargs"]),
        "segmented_resume": profile["segmented_resume"],
        "job_profile": job_profile.model_dump(mode="json"),
    }

    interview_and_behavioral_signals: Dict[str, Any] = {
        "_note": (
            "Caller-supplied placeholder values — NOT derived from parsing "
            "the resume/JD above. These stand in for live interview "
            "capture, gaze tracking, and code-execution infrastructure "
            "that does not exist yet on this platform (see backlog #13 "
            "and #66)."
        ),
        "screening_score": profile["screening_score"],
        "hr_answer": profile["hr_answer"],
        "technical_answers": profile["technical_answers"],
        "machine_test_submission": profile["machine_test_submission"],
        "visual_behavior_signals": profile["visual_behavior_signals"],
        "integrity_events": profile["integrity_events"],
    }

    return {
        "resume_and_job_data": resume_and_job_data,
        "interview_and_behavioral_signals": interview_and_behavioral_signals,
    }


def save_input_json(profiles: List[Dict[str, Any]], path: str) -> str:
    """Save the full Day 63 demo dataset's INPUT data to a JSON file.

    Mirrors save_json_output()'s pattern exactly: creates the destination
    directory if it does not already exist, then writes one record per
    candidate.

    Args:
        profiles: The list of demo profile dicts, as produced by
            build_demo_profiles().
        path: Destination file path for the JSON output.

    Returns:
        The absolute path the JSON file was written to.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)

    records = [build_input_record(profile) for profile in profiles]

    # `default=str` is a safety-net fallback only, mirroring
    # save_json_output()'s rationale: _serialize_value() already converts
    # every Pydantic model (including nested datetime/enum fields, via
    # model_dump(mode="json")) to JSON-safe primitives, and the remaining
    # profile values are plain hand-authored dicts/lists/strings/floats.
    # This just guards against json.dump() raising a TypeError if any
    # stray non-JSON-serializable value slips through.
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, default=str)

    return os.path.abspath(path)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the Day 63 demo dataset through the full 9-module system.

    Runs run_candidate_pipeline() for each fixed demo profile, prints a
    detailed 10-section report block per candidate, finishes with a
    summary table across all candidates, and saves the full run to
    data/demo/day63_demo_dataset.json (pipeline OUTPUT) and
    data/demo/day63_demo_dataset_input.json (the INPUT data that produced
    it — see DAY63B_DECISIONS.md). Purely a demonstration of the existing,
    tested per-module pipelines on authored demo data — not a claim of
    production readiness or real-world accuracy.
    """
    logger.info("Starting Day 63 demo dataset run")

    profiles = build_demo_profiles()
    results: List[Dict[str, Any]] = []

    for profile in profiles:
        result = run_candidate_pipeline(profile)
        results.append(result)
        print_candidate_report(profile, result)

    print_summary_table(profiles, results)

    saved_path = save_json_output(profiles, results, JSON_OUTPUT_PATH)
    print(f"JSON demo dataset saved to: {saved_path}")

    saved_input_path = save_input_json(profiles, INPUT_JSON_OUTPUT_PATH)
    print(f"JSON demo dataset input saved to: {saved_input_path}")

    logger.info("Completed Day 63 demo dataset run")


if __name__ == "__main__":
    main()
