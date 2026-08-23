"""
tests/simulate_full_system_day56.py

Demonstration / calibration script for Zecpath AI — Sprint 3, Day 56.

This script exercises the full 9-module hiring pipeline end-to-end for the
first time on four fixed, hand-authored QE-sector candidate profiles:

    ATS (ats_engine/) -> HR interview (interview_ai/: communication,
    behavior, hr_scoring, summary) -> technical_ai/ -> machine_test_ai/ ->
    visual_behavior_ai/ -> integrity_ai/ -> decision_ai/ (5-round unified
    scoring) -> final_decision_ai/ (risk-adjusted final decision) ->
    hiring_report_ai/ (compiled recruiter report).

It is NOT a claim of production status, is NOT connected to any live API,
does NOT use real candidate data, and its results are NOT a validated
claim of real-world accuracy or AI-vs-human agreement.

SCREENING NOTE: screening_ai's pipeline is NOT invoked live in this script.
Per Day 40/45 project precedent, screening_ai is already independently
validated (Day 30/32/40) and is not part of what this script needs to newly
prove. Every candidate's screening_score below is a FIXED, HAND-AUTHORED
float chosen to be consistent with that candidate's overall calibre — it is
NOT a live screening_ai result. See DAY56_DECISIONS.md for the full
rationale.

MACHINE TEST DOMAIN NOTE: machine_test_ai/machine_test_scoring.py is a
documented, accepted platform precedent for a generic software-engineering
task track — it is NOT QE-sector-specific content. Its use below is
generic-track filler for pipeline-completeness purposes only, consistent
with its own module docstring's "DOMAIN-DEVIATION NOTICE".

AI VS HUMAN COMPARISON / ACCURACY: no real human-evaluator ground truth
exists anywhere on this platform except Sprint 1's already-calibrated
20-candidate ATS test suite. This script does NOT compute or print any
"AI vs human accuracy", "match rate", or "score correlation" percentage.
Any mismatches between what a given module concluded and what might
intuitively be expected are genuine findings, reported honestly, not
smoothed over (same as Day 30/40/45 precedent).

PERFORMANCE / TIMING: not measured. No per-stage timing, latency, or
throughput benchmark exists for this pipeline as of Day 56 (consistent
with Day 42/54 precedent).

This is NOT a pytest file (same category as
tests/simulate_full_candidate_journey.py, the Day 45 script this one is
modeled on) — it is a manual demonstration/calibration script, deliberately
excluded from the pytest suite. Run it manually with:

    python -m tests.simulate_full_system_day56

No random module is used anywhere in this script; all demo data below is
fixed and hand-authored.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

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
# Demo candidate profiles
# ---------------------------------------------------------------------------


def build_demo_profiles() -> List[Dict[str, Any]]:
    """Build the fixed set of hand-authored QE-sector demo candidate profiles.

    Four profiles are defined:
        1. senior_full_qe_journey        — senior, automotive_quality, all
           5 rounds present.
        2. mid_partial_qe_journey        — mid, food_safety_systems,
           machine_test round deliberately MISSING (exercises decision_ai's
           proportional weight redistribution).
        3. fresher_qe_journey            — fresher, pharmaceutical_quality,
           weak/short answers throughout (exercises the low end of every
           module's decision bands).
        4. flagged_integrity_qe_journey  — mid, automotive_quality,
           otherwise-decent scores but integrity event counts high enough
           to trigger "High Risk" and genuinely flip final_decision_ai's
           risk-adjusted recommendation relative to decision_ai's base
           recommendation.

    No random module is used — every value below is fixed and authored by
    hand for calibration/demonstration purposes only.

    Returns:
        A list of profile dicts, each fully self-describing for every
        pipeline stage (see per-key comments inline).
    """
    return [
        # =====================================================================
        # 1. senior_full_qe_journey — automotive_quality, senior, full 5 rounds
        # =====================================================================
        {
            "candidate_id": "senior_full_qe_journey",
            "skill_domain": "automotive_quality",
            "role_level": InterviewRoleLevel.senior,
            "job_title_display": "Senior Quality Engineer — Automotive",
            "candidate_profile_kwargs": dict(
                candidate_id="senior_full_qe_journey",
                full_name="Ananya Rajan",
                email="ananya.rajan@example.com",
                phone="+91-9000000001",
                location="Pune, Maharashtra",
                is_actively_looking=True,
                skills=[
                    SkillObject(name="FMEA", level=SkillLevel.expert, years_of_experience=8.0, is_primary_skill=True),
                    SkillObject(name="Control Plans", level=SkillLevel.advanced, years_of_experience=7.0, is_primary_skill=True),
                    SkillObject(name="SPC", level=SkillLevel.advanced, years_of_experience=8.0, is_primary_skill=True),
                    SkillObject(name="PPAP", level=SkillLevel.expert, years_of_experience=7.0, is_primary_skill=True),
                    SkillObject(name="APQP", level=SkillLevel.advanced, years_of_experience=6.0, is_primary_skill=True),
                    SkillObject(name="CAPA", level=SkillLevel.intermediate, years_of_experience=5.0, is_primary_skill=False),
                    SkillObject(name="8D", level=SkillLevel.advanced, years_of_experience=6.0, is_primary_skill=False),
                    SkillObject(name="RCA", level=SkillLevel.advanced, years_of_experience=6.0, is_primary_skill=False),
                    SkillObject(name="IATF 16949", level=SkillLevel.expert, years_of_experience=7.0, is_primary_skill=True),
                ],
                experience=[
                    ExperienceObject(
                        company_name="TataAuto Components Ltd",
                        role_title="Quality Engineer",
                        department="Quality Assurance",
                        company_type=CompanyType.mnc,
                        location="Pune, Maharashtra",
                        employment_type=EmploymentType.fulltime,
                        start_date="2019-04",
                        end_date=None,
                        is_current=True,
                        duration_months=60,
                        responsibilities=[
                            "Own FMEA and control plan development for new programs.",
                            "Lead PPAP submissions and APQP milestones with suppliers.",
                        ],
                        technologies_used=["FMEA", "PPAP", "APQP", "SPC", "IATF 16949"],
                        achievements=["Reduced supplier PPAP rejection rate by 30%."],
                    ),
                    ExperienceObject(
                        company_name="Bosch Auto Parts",
                        role_title="Quality Engineer",
                        department="Quality",
                        company_type=CompanyType.mnc,
                        location="Bangalore, Karnataka",
                        employment_type=EmploymentType.fulltime,
                        start_date="2014-05",
                        end_date="2019-03",
                        is_current=False,
                        duration_months=36,
                        responsibilities=["Ran SPC monitoring on production lines.", "Led 8D/RCA investigations."],
                        technologies_used=["SPC", "8D", "RCA"],
                        achievements=["Closed 40+ CAPAs with zero repeat findings."],
                    ),
                ],
                education=[
                    EducationObject(
                        degree="B.Tech",
                        field_of_study="Mechanical Engineering",
                        institution_name="College of Engineering Pune",
                        location="Pune, Maharashtra",
                        start_year=2008,
                        end_year=2012,
                        grade="8.2",
                        grade_type=GradeType.cgpa,
                        is_highest_qualification=True,
                    ),
                ],
                certifications=[
                    CertificationObject(
                        name="Six Sigma Black Belt",
                        issuing_organization="ASQ",
                        issue_date="2015-06",
                        expiry_date=None,
                        credential_id="ASQ-SSBB-1001",
                        is_expired=False,
                    ),
                    CertificationObject(
                        name="ASQ CQE",
                        issuing_organization="ASQ",
                        issue_date="2016-01",
                        expiry_date=None,
                        credential_id="ASQ-CQE-1002",
                        is_expired=False,
                    ),
                    CertificationObject(
                        name="IATF 16949 Lead Auditor",
                        issuing_organization="Bureau Veritas",
                        issue_date="2018-03",
                        expiry_date=None,
                        credential_id="BV-IATF-1003",
                        is_expired=False,
                    ),
                ],
                languages_known=["English", "Hindi", "Marathi"],
                expected_salary_inr=1300000,
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
                            "IATF 16949, Six Sigma Black Belt, supplier quality management."
                        ),
                    },
                    {
                        "section": "experience",
                        "content": (
                            "Senior Quality Engineer leading FMEA and control plan "
                            "development for new automotive programs, owning PPAP "
                            "submissions and APQP milestones with suppliers, running "
                            "SPC-based process monitoring, and closing CAPAs via 8D "
                            "and root cause analysis for IATF 16949 compliance."
                        ),
                    },
                ]
            },
            "screening_score": 82.0,  # fixed, hand-authored — see module docstring
            "hr_answer": {
                "question_id": "Q1",
                "answer_text": (
                    "In my current role I led the FMEA and control plan redesign "
                    "for a new brake component program after we saw a rise in "
                    "field returns. First, I pulled the failure data and traced "
                    "the root cause to a tolerance stack-up issue in the "
                    "supplier's control plan. Then, I revised the control plan "
                    "and tightened the SPC limits on the critical dimension. As "
                    "a result, the defect rate dropped by more than half within "
                    "two quarters. I coordinated the PPAP resubmission with the "
                    "supplier and made sure the APQP timeline stayed on track. "
                    "Because IATF 16949 compliance mattered for the launch, I "
                    "documented every change through our CAPA process and ran "
                    "an 8D with the supplier's quality team. Finally, I trained "
                    "the line inspectors on the new control plan so the gains "
                    "would hold going forward."
                ),
                "duration_seconds": 45.0,
                "relevance_score": 0.93,
                "is_vague": False,
            },
            "technical_answers": [
                {
                    "question_id": "T1",
                    "phase": "experience_based",
                    "accuracy": 0.92,
                    "text": (
                        "On the production line, we had a recurring dimensional "
                        "deviation. First I ran a root cause analysis, which "
                        "meant pulling the SPC charts and the control plan "
                        "together. Because the tolerance was tight, small tool "
                        "wear had a real impact. Therefore we added a control "
                        "point and, as a result, deviations dropped sharply. "
                        "In practice this is a trade-off between inspection "
                        "frequency and cycle time, which we validated during "
                        "an audit."
                    ),
                },
                {
                    "question_id": "T2",
                    "phase": "scenario_based",
                    "accuracy": 0.88,
                    "text": (
                        "If a supplier's PPAP submission shows a marginal "
                        "capability index, I would first review the control "
                        "plan and specification together, then request updated "
                        "process data. This matters because the risk of field "
                        "failure increases with any tolerance drift, so in our "
                        "facility we would hold the part on a deviation until "
                        "root cause is confirmed."
                    ),
                },
                {
                    "question_id": "T3",
                    "phase": "conceptual",
                    "accuracy": 0.9,
                    "text": (
                        "APQP exists so that risk is managed before mass "
                        "production, which means FMEA, control plans, and PPAP "
                        "are all linked. Because of this, a specification "
                        "change late in the program has a large impact on "
                        "timeline and cost, which we saw for example during a "
                        "real-world program launch."
                    ),
                },
            ],
            "machine_test_submission": {
                "passed_test_count": 9,
                "total_test_count": 10,
                "runtime_seconds": 1.8,
                "runtime_baseline_seconds": 2.0,
                "code_quality": 0.85,
                "attempts": 2,
                "time_taken_seconds": 900.0,
                "time_limit_seconds": 1200.0,
            },
            "visual_behavior_signals": {
                "gaze_stability": 0.88,
                "head_stability": 0.85,
                "facial_engagement": 0.82,
                "attention_consistency": 0.86,
            },
            "integrity_events": {
                "tab_switch_count": 0,
                "focus_loss_count": 1,
                "external_voice_count": 0,
                "gaze_deviation_count": 1,
            },
        },
        # =====================================================================
        # 2. mid_partial_qe_journey — food_safety_systems, mid,
        #    machine_test round deliberately MISSING
        # =====================================================================
        {
            "candidate_id": "mid_partial_qe_journey",
            "skill_domain": "food_safety_systems",
            "role_level": InterviewRoleLevel.mid,
            "job_title_display": "Quality Engineer — Food Safety Systems",
            "candidate_profile_kwargs": dict(
                candidate_id="mid_partial_qe_journey",
                full_name="Rohit Verma",
                email="rohit.verma@example.com",
                phone="+91-9000000002",
                location="Anand, Gujarat",
                is_actively_looking=True,
                skills=[
                    SkillObject(name="HACCP", level=SkillLevel.advanced, years_of_experience=4.0, is_primary_skill=True),
                    SkillObject(name="GMP", level=SkillLevel.advanced, years_of_experience=5.0, is_primary_skill=True),
                    SkillObject(name="SQF", level=SkillLevel.intermediate, years_of_experience=3.0, is_primary_skill=True),
                    SkillObject(name="ISO 22000", level=SkillLevel.intermediate, years_of_experience=4.0, is_primary_skill=False),
                    SkillObject(name="FSSC 22000", level=SkillLevel.intermediate, years_of_experience=3.0, is_primary_skill=False),
                    SkillObject(name="CAPA", level=SkillLevel.intermediate, years_of_experience=3.0, is_primary_skill=False),
                    SkillObject(name="RCA", level=SkillLevel.intermediate, years_of_experience=3.0, is_primary_skill=False),
                ],
                experience=[
                    ExperienceObject(
                        company_name="FreshDairy Foods Pvt Ltd",
                        role_title="Quality Engineer",
                        department="Quality Assurance",
                        company_type=CompanyType.mnc,
                        location="Anand, Gujarat",
                        employment_type=EmploymentType.fulltime,
                        start_date="2020-06",
                        end_date=None,
                        is_current=True,
                        duration_months=48,
                        responsibilities=[
                            "Maintain HACCP plans and GMP compliance across production lines.",
                            "Support SQF and ISO 22000 / FSSC 22000 audits.",
                        ],
                        technologies_used=["HACCP", "GMP", "SQF", "ISO 22000"],
                        achievements=["Passed two consecutive FSSC 22000 surveillance audits with zero major findings."],
                    ),
                ],
                education=[
                    EducationObject(
                        degree="B.Tech",
                        field_of_study="Food Technology",
                        institution_name="Anand Agricultural University",
                        location="Anand, Gujarat",
                        start_year=2015,
                        end_year=2019,
                        grade="7.6",
                        grade_type=GradeType.cgpa,
                        is_highest_qualification=True,
                    ),
                ],
                certifications=[
                    CertificationObject(
                        name="HACCP",
                        issuing_organization="Codex Alimentarius",
                        issue_date="2019-08",
                        expiry_date=None,
                        credential_id="CA-HACCP-2001",
                        is_expired=False,
                    ),
                    CertificationObject(
                        name="FSSC 22000",
                        issuing_organization="FSSC",
                        issue_date="2020-02",
                        expiry_date=None,
                        credential_id="FSSC-2002",
                        is_expired=False,
                    ),
                ],
                languages_known=["English", "Hindi", "Gujarati"],
                expected_salary_inr=800000,
                notice_period_days=45,
                raw_text=None,
                parsing_metadata=_demo_parsing_metadata(),
            ),
            "segmented_resume": {
                "sections": [
                    {
                        "section": "skills",
                        "content": (
                            "HACCP, GMP, SQF, ISO 22000, FSSC 22000, CAPA, root "
                            "cause analysis, food safety audits."
                        ),
                    },
                    {
                        "section": "experience",
                        "content": (
                            "Quality Engineer maintaining HACCP plans and GMP "
                            "compliance across dairy production lines, "
                            "supporting SQF and ISO 22000 / FSSC 22000 "
                            "certification audits."
                        ),
                    },
                ]
            },
            "screening_score": 70.0,  # fixed, hand-authored — see module docstring
            "hr_answer": {
                "question_id": "Q1",
                "answer_text": (
                    "In my current role I mostly work on maintaining our HACCP "
                    "plan and GMP compliance across two production lines. For "
                    "example, last year during a surveillance audit we found a "
                    "gap in our monitoring records, so I updated the checklist "
                    "and retrained the line staff. I usually start by checking "
                    "the CCP logs and recent deviations to see if anything "
                    "needs escalation."
                ),
                "duration_seconds": 26.0,
                "relevance_score": 0.72,
                "is_vague": False,
            },
            "technical_answers": [
                {
                    "question_id": "T1",
                    "phase": "experience_based",
                    "accuracy": 0.72,
                    "text": (
                        "In our facility we had a CCP monitoring gap. First we "
                        "reviewed the HACCP plan, then updated the checklist. "
                        "Because the risk to product safety was real, we also "
                        "retrained staff, for example on correct temperature "
                        "logging."
                    ),
                },
                {
                    "question_id": "T2",
                    "phase": "conceptual",
                    "accuracy": 0.68,
                    "text": (
                        "GMP and HACCP work together because HACCP identifies "
                        "the risk points and GMP covers the general hygiene "
                        "practices around them, which means both are needed for "
                        "an SQF audit to pass."
                    ),
                },
            ],
            "machine_test_submission": None,  # deliberately missing round
            "visual_behavior_signals": {
                "gaze_stability": 0.66,
                "head_stability": 0.7,
                "facial_engagement": 0.6,
                "attention_consistency": 0.65,
            },
            "integrity_events": {
                "tab_switch_count": 1,
                "focus_loss_count": 1,
                "external_voice_count": 0,
                "gaze_deviation_count": 2,
            },
        },
        # =====================================================================
        # 3. fresher_qe_journey — pharmaceutical_quality, fresher, weak
        #    answers throughout, full 5 rounds
        # =====================================================================
        {
            "candidate_id": "fresher_qe_journey",
            "skill_domain": "pharmaceutical_quality",
            "role_level": InterviewRoleLevel.fresher,
            "job_title_display": "Quality Engineer — Pharmaceutical (Entry Level)",
            "candidate_profile_kwargs": dict(
                candidate_id="fresher_qe_journey",
                full_name="Sneha Iyer",
                email="sneha.iyer@example.com",
                phone="+91-9000000003",
                location="Hyderabad, Telangana",
                is_actively_looking=True,
                skills=[
                    SkillObject(name="GMP Pharmaceutical", level=SkillLevel.beginner, years_of_experience=0.5, is_primary_skill=True),
                    SkillObject(name="CAPA", level=SkillLevel.beginner, years_of_experience=0.5, is_primary_skill=False),
                    SkillObject(name="GxP", level=SkillLevel.beginner, years_of_experience=0.5, is_primary_skill=False),
                ],
                experience=[
                    ExperienceObject(
                        company_name="PharmaCare Labs",
                        role_title="Quality Engineer",
                        department="Quality",
                        company_type=CompanyType.mnc,
                        location="Hyderabad, Telangana",
                        employment_type=EmploymentType.internship,
                        start_date="2024-01",
                        end_date="2024-06",
                        is_current=False,
                        duration_months=6,
                        responsibilities=["Assisted with batch record review."],
                        technologies_used=["GMP Pharmaceutical"],
                        achievements=[],
                    ),
                ],
                education=[
                    EducationObject(
                        degree="B.Pharma",
                        field_of_study="Pharmacy",
                        institution_name="Osmania University",
                        location="Hyderabad, Telangana",
                        start_year=2020,
                        end_year=2024,
                        grade="65%",
                        grade_type=GradeType.percentage,
                        is_highest_qualification=True,
                    ),
                ],
                certifications=[],
                languages_known=["English", "Telugu", "Hindi"],
                expected_salary_inr=300000,
                notice_period_days=15,
                raw_text=None,
                parsing_metadata=_demo_parsing_metadata(),
            ),
            "segmented_resume": {
                "sections": [
                    {
                        "section": "skills",
                        "content": "GMP Pharmaceutical, CAPA basics, GxP awareness.",
                    },
                    {
                        "section": "experience",
                        "content": (
                            "Intern assisting with batch record review in a "
                            "pharmaceutical quality department."
                        ),
                    },
                ]
            },
            "screening_score": 42.0,  # fixed, hand-authored — see module docstring
            "hr_answer": {
                "question_id": "Q1",
                "answer_text": (
                    "I did an internship where I helped review batch records. "
                    "It was mostly checking paperwork. I did not handle any "
                    "audits myself."
                ),
                "duration_seconds": 8.0,
                "relevance_score": 0.4,
                "is_vague": True,
            },
            "technical_answers": [
                {
                    "question_id": "T1",
                    "phase": "experience_based",
                    "accuracy": 0.35,
                    "text": "I checked batch records for missing signatures.",
                },
                {
                    "question_id": "T2",
                    "phase": "conceptual",
                    "accuracy": 0.3,
                    "text": "GMP is about following procedures correctly.",
                },
            ],
            "machine_test_submission": {
                "passed_test_count": 3,
                "total_test_count": 10,
                "runtime_seconds": 4.5,
                "runtime_baseline_seconds": 2.0,
                "code_quality": 0.35,
                "attempts": 5,
                "time_taken_seconds": 1180.0,
                "time_limit_seconds": 1200.0,
            },
            "visual_behavior_signals": {
                "gaze_stability": 0.42,
                "head_stability": 0.45,
                "facial_engagement": 0.38,
                "attention_consistency": 0.4,
            },
            "integrity_events": {
                "tab_switch_count": 2,
                "focus_loss_count": 2,
                "external_voice_count": 1,
                "gaze_deviation_count": 2,
            },
        },
        # =====================================================================
        # 4. flagged_integrity_qe_journey — automotive_quality, mid, decent
        #    scores but integrity events high enough to flip the final
        #    recommendation relative to decision_ai's base recommendation
        # =====================================================================
        {
            "candidate_id": "flagged_integrity_qe_journey",
            "skill_domain": "automotive_quality",
            "role_level": InterviewRoleLevel.mid,
            "job_title_display": "Quality Engineer — Automotive",
            "candidate_profile_kwargs": dict(
                candidate_id="flagged_integrity_qe_journey",
                full_name="Karan Mehta",
                email="karan.mehta@example.com",
                phone="+91-9000000004",
                location="Chennai, Tamil Nadu",
                is_actively_looking=True,
                skills=[
                    SkillObject(name="FMEA", level=SkillLevel.advanced, years_of_experience=4.0, is_primary_skill=True),
                    SkillObject(name="Control Plans", level=SkillLevel.intermediate, years_of_experience=3.0, is_primary_skill=True),
                    SkillObject(name="SPC", level=SkillLevel.advanced, years_of_experience=4.0, is_primary_skill=True),
                    SkillObject(name="PPAP", level=SkillLevel.advanced, years_of_experience=4.0, is_primary_skill=True),
                    SkillObject(name="APQP", level=SkillLevel.intermediate, years_of_experience=3.0, is_primary_skill=True),
                    SkillObject(name="CAPA", level=SkillLevel.intermediate, years_of_experience=3.0, is_primary_skill=False),
                    SkillObject(name="8D", level=SkillLevel.intermediate, years_of_experience=3.0, is_primary_skill=False),
                    SkillObject(name="IATF 16949", level=SkillLevel.advanced, years_of_experience=4.0, is_primary_skill=True),
                ],
                experience=[
                    ExperienceObject(
                        company_name="AutoParts Manufacturing Ltd",
                        role_title="Quality Engineer",
                        department="Quality Assurance",
                        company_type=CompanyType.mnc,
                        location="Chennai, Tamil Nadu",
                        employment_type=EmploymentType.fulltime,
                        start_date="2020-07",
                        end_date=None,
                        is_current=True,
                        duration_months=48,
                        responsibilities=[
                            "Support FMEA and control plan reviews.",
                            "Run SPC monitoring and PPAP coordination with suppliers.",
                        ],
                        technologies_used=["FMEA", "SPC", "PPAP", "APQP", "IATF 16949"],
                        achievements=["Improved SPC out-of-control response time by 25%."],
                    ),
                ],
                education=[
                    EducationObject(
                        degree="B.Tech",
                        field_of_study="Mechanical Engineering",
                        institution_name="Anna University",
                        location="Chennai, Tamil Nadu",
                        start_year=2016,
                        end_year=2020,
                        grade="7.9",
                        grade_type=GradeType.cgpa,
                        is_highest_qualification=True,
                    ),
                ],
                certifications=[
                    CertificationObject(
                        name="Six Sigma Green Belt",
                        issuing_organization="ASQ",
                        issue_date="2021-05",
                        expiry_date=None,
                        credential_id="ASQ-SSGB-3001",
                        is_expired=False,
                    ),
                    CertificationObject(
                        name="ASQ CQE",
                        issuing_organization="ASQ",
                        issue_date="2022-02",
                        expiry_date=None,
                        credential_id="ASQ-CQE-3002",
                        is_expired=False,
                    ),
                ],
                languages_known=["English", "Tamil", "Hindi"],
                expected_salary_inr=900000,
                notice_period_days=30,
                raw_text=None,
                parsing_metadata=_demo_parsing_metadata(),
            ),
            "segmented_resume": {
                "sections": [
                    {
                        "section": "skills",
                        "content": (
                            "FMEA, Control Plans, SPC, PPAP, APQP, CAPA, 8D, "
                            "IATF 16949, Six Sigma Green Belt."
                        ),
                    },
                    {
                        "section": "experience",
                        "content": (
                            "Quality Engineer supporting FMEA and control plan "
                            "reviews, running SPC monitoring, and coordinating "
                            "PPAP submissions with suppliers under IATF 16949."
                        ),
                    },
                ]
            },
            "screening_score": 78.0,  # fixed, hand-authored — see module docstring
            "hr_answer": {
                "question_id": "Q1",
                "answer_text": (
                    "In my current role I support FMEA and control plan "
                    "reviews for new parts. First, I check the SPC data for "
                    "any drift, then flag it to the lead engineer. Because "
                    "PPAP timelines are tight, I coordinate closely with "
                    "suppliers so nothing slips. As a result, our last three "
                    "launches stayed on schedule with no major deviations."
                ),
                "duration_seconds": 34.0,
                "relevance_score": 0.8,
                "is_vague": False,
            },
            "technical_answers": [
                {
                    "question_id": "T1",
                    "phase": "experience_based",
                    "accuracy": 0.82,
                    "text": (
                        "First I reviewed the SPC chart, then flagged the "
                        "drift, because the tolerance risk was high. As a "
                        "result we caught the deviation before it reached the "
                        "customer, which we confirmed during an audit."
                    ),
                },
                {
                    "question_id": "T2",
                    "phase": "scenario_based",
                    "accuracy": 0.78,
                    "text": (
                        "If PPAP capability looked marginal, I would check the "
                        "specification and control plan together, because the "
                        "risk of a field issue matters, so that we hold the "
                        "part until root cause is confirmed."
                    ),
                },
            ],
            "machine_test_submission": {
                "passed_test_count": 8,
                "total_test_count": 10,
                "runtime_seconds": 2.0,
                "runtime_baseline_seconds": 2.0,
                "code_quality": 0.78,
                "attempts": 2,
                "time_taken_seconds": 950.0,
                "time_limit_seconds": 1200.0,
            },
            "visual_behavior_signals": {
                "gaze_stability": 0.75,
                "head_stability": 0.72,
                "facial_engagement": 0.7,
                "attention_consistency": 0.74,
            },
            # Deliberately chosen to exceed EVERY WARNING_THRESHOLDS value and
            # meet/exceed every EVENT_CAPS value, per integrity_scoring.py
            # (attached): tab_switch_count cap=5, focus_loss_count cap=5,
            # external_voice_count cap=3, gaze_deviation_count cap=5;
            # warning thresholds are 3 / 3 / 2 / 3 respectively. All four
            # signals bottom out at 0.0, giving integrity_score=0.0 and
            # risk_level="High Risk" (>= a genuine, non-fabricated result of
            # the real formula in integrity_scoring.py, not hand-picked to
            # hit a label).
            "integrity_events": {
                "tab_switch_count": 6,
                "focus_loss_count": 6,
                "external_voice_count": 4,
                "gaze_deviation_count": 6,
            },
        },
    ]


# ---------------------------------------------------------------------------
# Pipeline orchestration
# ---------------------------------------------------------------------------


def run_candidate_pipeline(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Run the full 9-module hiring pipeline for one candidate profile.

    Stage order: ATS -> screening (fixed float) -> HR interview
    (communication/behavior/hr_scoring/summary) -> technical_ai ->
    machine_test_ai (skipped if profile["machine_test_submission"] is None)
    -> visual_behavior_ai -> integrity_ai -> decision_ai (5-round unified
    scoring) -> final_decision_ai -> hiring_report_ai.

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

    # ---- 5. Machine test (skipped for mid_partial_qe_journey) ---------------
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
    print("SUMMARY TABLE — ALL CANDIDATES (Day 56 full-system run)")
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
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the full 9-module system demonstration for all demo profiles.

    Runs run_candidate_pipeline() for each fixed demo profile, prints a
    detailed 10-section report block per candidate, and finishes with a
    summary table across all candidates. Purely a demonstration of the
    existing, tested per-module pipelines on authored demo data — not a
    claim of production readiness or real-world accuracy.
    """
    logger.info("Starting Day 56 full-system demonstration")

    profiles = build_demo_profiles()
    results: List[Dict[str, Any]] = []

    for profile in profiles:
        result = run_candidate_pipeline(profile)
        results.append(result)
        print_candidate_report(profile, result)

    print_summary_table(profiles, results)

    logger.info("Completed Day 56 full-system demonstration")


if __name__ == "__main__":
    main()
