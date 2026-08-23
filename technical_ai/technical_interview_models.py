"""
technical_ai/technical_interview_models.py

Pydantic v2 models for the Technical Interview Engine question bank and
live state.
Part of Zecpath AI — Day 46.

CRITICAL: No imports from interview_ai, screening_ai, ats_engine, or any
other existing project module — technical_ai is fully self-contained.
This follows the same cross-module isolation rule documented in
interview_ai/interview_models.py; technical_ai is a separate top-level
module with its own, deliberately independent, tiering concept
(TechnicalDifficulty). It is NOT interchangeable with interview_ai's
RoleLevel — see resolve_technical_difficulty() docstring below and
technical_ai/DAY46_DECISIONS.md for full rationale.
"""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class TechnicalSkillDomain(str, Enum):
    """
    QE (Quality Engineering) sector domains covered by the technical
    interview track. A question bank is scoped to exactly one domain.
    """

    automotive_quality = "automotive_quality"
    food_safety_systems = "food_safety_systems"
    pharmaceutical_quality = "pharmaceutical_quality"


class TechnicalDifficulty(str, Enum):
    """
    Difficulty tiers for technical interview questions, derived from a
    candidate's total months of experience via resolve_technical_difficulty().

    Deliberately a separate concept from interview_ai.interview_models
    .RoleLevel — different boundaries, different purpose, no cross-reference
    or conversion between the two. See DAY46_DECISIONS.md.
    """

    basic = "basic"
    intermediate = "intermediate"
    advanced = "advanced"


class TechnicalInterviewPhase(str, Enum):
    """
    Ordered phases of the technical interview flow.

    Declaration order (introduction → experience_based → conceptual →
    scenario_based → closing) is the authoritative sort key used by
    TechnicalQuestionBankManager.generate_interview_questions() to
    sequence questions across phases deterministically without any
    random sampling.

    Note: unlike interview_ai (which splits phase and category into two
    separate enums), this module treats phase and category as the same
    concept — there is no separate category enum here.
    """

    introduction = "introduction"
    experience_based = "experience_based"
    conceptual = "conceptual"
    scenario_based = "scenario_based"
    closing = "closing"


# ---------------------------------------------------------------------------
# Difficulty resolution
# ---------------------------------------------------------------------------

# Difficulty tier boundaries, stored in MONTHS for consistency with the
# rest of the platform (CandidateProfile.total_experience_months
# convention), but derived from the Day 46 task brief's year-based
# spec: 0-2 years -> basic, 3-5 years -> intermediate, 5+ years -> advanced.
BASIC_MAX_MONTHS: int = 24  # 0-2 years
INTERMEDIATE_MAX_MONTHS: int = 60  # 3-5 years


def resolve_technical_difficulty(total_experience_months: int) -> TechnicalDifficulty:
    """
    Derive a TechnicalDifficulty tier from a candidate's total months of
    experience, per the Day 46 task brief's explicit year boundaries.

    < 24 months        -> TechnicalDifficulty.basic
    24 to 60 months     -> TechnicalDifficulty.intermediate
    61+ months          -> TechnicalDifficulty.advanced

    NOTE: This is a deliberately separate concept from
    interview_ai.interview_models.RoleLevel / resolve_role_level(), which
    uses different boundaries (fresher <12mo, mid 12-84mo, senior 84+)
    for HR-round question applicability. TechnicalDifficulty governs
    technical-question progression only. Do not conflate the two.

    Pure function, no side effects, no randomness.

    Args:
        total_experience_months: Candidate's total experience in months.

    Returns:
        The corresponding TechnicalDifficulty enum member.
    """
    if total_experience_months < BASIC_MAX_MONTHS:
        return TechnicalDifficulty.basic
    elif total_experience_months <= INTERMEDIATE_MAX_MONTHS:
        return TechnicalDifficulty.intermediate
    else:
        return TechnicalDifficulty.advanced


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class TechnicalInterviewQuestion(BaseModel):
    """
    Represents a single technical interview question.

    Each question carries metadata for filtering by skill domain, phase,
    and applicable difficulty tiers, and for ordering within a generated
    interview sequence.

    The `order` field is the sole mechanism for deterministic sequencing —
    no random selection is performed anywhere in this module or in
    TechnicalQuestionBankManager.

    question_id format: "TQ_<DOMAIN_ABBR>_<PHASE_ABBR>_NNN"
        DOMAIN_ABBR: AUTO (automotive_quality), FOOD (food_safety_systems),
                     PHARMA (pharmaceutical_quality)
        PHASE_ABBR : INTRO (introduction), EXP (experience_based),
                     CONC (conceptual), SCEN (scenario_based),
                     CLOSE (closing)
        e.g. TQ_AUTO_EXP_001, TQ_FOOD_CONC_002, TQ_PHARMA_SCEN_001
    """

    question_id: str = Field(
        ..., description="Unique identifier, e.g. TQ_AUTO_EXP_001"
    )
    text: str = Field(
        ..., description="The question as presented to the candidate"
    )
    skill_domain: TechnicalSkillDomain = Field(
        ..., description="QE sector domain this question belongs to"
    )
    phase: TechnicalInterviewPhase = Field(
        ..., description="Technical interview phase this question belongs to"
    )
    applicable_difficulties: List[TechnicalDifficulty] = Field(
        default_factory=list,
        description="Difficulty tiers this question is appropriate for; "
        "empty list is invalid, must contain at least one tier",
    )
    order: int = Field(
        ...,
        description=(
            "Global sequential position used for deterministic sorting "
            "within a phase. NOT a random-selection weight."
        ),
    )
    follow_up_eligible: bool = Field(
        default=True,
        description=(
            "Whether the conversation engine may ask a follow-up "
            "for this question"
        ),
    )

    @field_validator("applicable_difficulties")
    @classmethod
    def _validate_applicable_difficulties_non_empty(
        cls, value: List[TechnicalDifficulty]
    ) -> List[TechnicalDifficulty]:
        """Ensure applicable_difficulties contains at least one tier."""
        if not value:
            raise ValueError(
                "applicable_difficulties must contain at least one "
                "TechnicalDifficulty tier; empty list is invalid"
            )
        return value


class TechnicalInterviewQuestionBank(BaseModel):
    """
    Full technical interview question bank for a specific job posting,
    scoped to exactly one skill domain (not mixed).
    """

    job_id: str = Field(
        ..., description="Unique job identifier associated with this bank"
    )
    skill_domain: TechnicalSkillDomain = Field(
        ...,
        description=(
            "The single QE sector domain this bank is scoped to; "
            "all questions in the bank must match this domain"
        ),
    )
    questions: List[TechnicalInterviewQuestion] = Field(
        ..., description="All technical interview questions in this bank"
    )
    total_questions: int = Field(
        ..., description="Total number of questions in this bank"
    )
    version: str = Field(
        default="1.0.0",
        description="Schema version for forward compatibility",
    )


class TechnicalInterviewState(BaseModel):
    """
    Live in-progress technical interview state. Mirrors interview_ai's
    InterviewState in shape and purpose, adapted for the technical track.

    Persistence (Redis key pattern, if any) is NOT decided in this design
    day — no Redis code in this module. This is a state SHAPE only; the
    engine that mutates it is future work (see DAY46_DECISIONS.md).
    """

    candidate_id: str = Field(..., description="Unique candidate identifier")
    job_id: str = Field(..., description="Job identifier this interview is for")
    skill_domain: TechnicalSkillDomain = Field(
        ..., description="QE sector domain this interview is scoped to"
    )
    current_phase: TechnicalInterviewPhase = Field(
        ..., description="The technical interview phase currently in progress"
    )
    current_difficulty: TechnicalDifficulty = Field(
        ...,
        description=(
            "Resolved difficulty tier currently in effect; mutable across "
            "the interview as difficulty adapts. The adaptation "
            "TRIGGER/SIGNAL is explicitly out of scope for this file — "
            "see DAY46_DECISIONS.md."
        ),
    )
    questions_asked: List[str] = Field(
        default_factory=list,
        description="List of question_ids already asked in this session",
    )
    current_question_id: Optional[str] = Field(
        default=None,
        description="The question_id currently being presented to the candidate",
    )
    completed: bool = Field(
        default=False,
        description="True when all phases have been completed",
    )
