"""
interview_ai/interview_models.py

Pydantic v2 models for the HR Interview Engine question bank and live state.
Part of Zecpath AI — Day 33, Sprint 4.

CRITICAL: No imports from screening_ai — this module is fully self-contained.
Duplicate enums (e.g. RoleLevel) are intentional; interview_ai follows the
same cross-module isolation rule as ats_engine, scoring, and screening_ai.
"""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

from utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class RoleLevel(str, Enum):
    """
    Candidate seniority levels for interview question applicability filtering.

    Intentionally duplicated from screening_ai.question_models.RoleLevel —
    interview_ai is a self-contained module; cross-module imports are
    prohibited by project convention.
    """

    fresher = "fresher"
    mid = "mid"
    senior = "senior"
    all_levels = "all_levels"


# Aligned with scoring/ats_scorer.py experience bands —
# fresher <12mo, mid 12-84mo, senior 84+
FRESHER_MAX_MONTHS: int = 12
MID_MAX_MONTHS: int = 84


def resolve_role_level(total_experience_months: int) -> RoleLevel:
    """
    Derive a RoleLevel from a candidate's total months of experience.

    Boundary rules are aligned with scoring/ats_scorer.py experience bands:
        < 12 months       → RoleLevel.fresher
        12 to 83 months   → RoleLevel.mid
        84+ months        → RoleLevel.senior

    This is a pure function — same input always produces the same output.
    No side effects; safe to call from tests without any setup.

    Args:
        total_experience_months: Candidate's total experience in months.

    Returns:
        The corresponding RoleLevel enum member.
    """
    if total_experience_months < FRESHER_MAX_MONTHS:
        return RoleLevel.fresher
    elif total_experience_months < MID_MAX_MONTHS:
        return RoleLevel.mid
    else:
        return RoleLevel.senior


class RoleType(str, Enum):
    """Distinguishes technical from non-technical interview tracks."""

    technical = "technical"
    non_technical = "non_technical"


class InterviewPhase(str, Enum):
    """
    Ordered phases of the HR interview flow.

    Declaration order (introduction → core_hr → role_based → closing) is
    the authoritative sort key used by InterviewQuestionBankManager
    .generate_interview_questions() to sequence questions across phases
    deterministically without any random sampling.
    """

    introduction = "introduction"
    core_hr = "core_hr"
    role_based = "role_based"
    closing = "closing"


class InterviewQuestionCategory(str, Enum):
    """Fine-grained categories that group interview questions by purpose."""

    introduction = "introduction"
    strengths_weaknesses = "strengths_weaknesses"
    teamwork_culture_fit = "teamwork_culture_fit"
    career_goals = "career_goals"
    availability = "availability"
    role_based_technical = "role_based_technical"
    role_based_non_technical = "role_based_non_technical"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class InterviewQuestion(BaseModel):
    """
    Represents a single HR interview question.

    Each question carries metadata for filtering by level, role type, and
    phase, and for ordering within a generated interview sequence.

    The `order` field is the sole mechanism for deterministic sequencing —
    no random selection is performed anywhere in this module or in
    InterviewQuestionBankManager.
    """

    question_id: str = Field(
        ..., description="Unique identifier, e.g. IQ_INTRO_001"
    )
    text: str = Field(
        ..., description="The question as presented to the candidate"
    )
    category: InterviewQuestionCategory = Field(
        ..., description="Fine-grained category this question belongs to"
    )
    phase: InterviewPhase = Field(
        ..., description="Interview phase this question belongs to"
    )
    applicable_levels: List[RoleLevel] = Field(
        default_factory=lambda: [RoleLevel.all_levels],
        description=(
            "Role levels this question applies to; "
            "all_levels means no level restriction"
        ),
    )
    applicable_role_types: List[RoleType] = Field(
        default_factory=lambda: [RoleType.technical, RoleType.non_technical],
        description="Interview tracks this question applies to",
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


class InterviewQuestionBank(BaseModel):
    """
    Full HR interview question bank for a specific job posting.

    Stored in Redis under key: interview_question_bank:{job_id}
    No TTL — persists until explicitly deleted.
    """

    job_id: str = Field(
        ..., description="Unique job identifier, matches Redis key suffix"
    )
    questions: List[InterviewQuestion] = Field(
        ..., description="All interview questions in this bank"
    )
    total_questions: int = Field(
        ..., description="Total number of questions in this bank"
    )
    version: str = Field(
        default="1.0.0",
        description="Schema version for forward compatibility",
    )


class InterviewState(BaseModel):
    """
    Tracks the live state of an in-progress HR interview for a candidate.

    Persisted and updated by the conversation engine (Day 34+) as the
    interview progresses through each phase.

    Redis key pattern: interview_state:{candidate_id}:{job_id}
    """

    candidate_id: str = Field(
        ..., description="Unique candidate identifier"
    )
    job_id: str = Field(
        ..., description="Job identifier this interview is for"
    )
    current_phase: InterviewPhase = Field(
        ..., description="The interview phase currently in progress"
    )
    role_level: RoleLevel = Field(
        ..., description="Resolved seniority level for this candidate"
    )
    role_type: RoleType = Field(
        ..., description="Interview track: technical or non_technical"
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
