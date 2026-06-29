"""
screening_ai/question_models.py

Pydantic v2 models for the HR Screening Question Bank.
Part of Zecpath AI — Day 22, Sprint 2.

Defines data structures for individual screening questions and the
full question bank stored per job_id in Redis.
"""

from enum import Enum
from typing import List
from pydantic import BaseModel, Field


class AnswerType(str, Enum):
    """Defines the expected format of a candidate's answer."""
    text = "text"
    number = "number"
    yes_no = "yes_no"
    list_items = "list_items"


class RoleLevel(str, Enum):
    """Candidate seniority levels for question applicability filtering."""
    fresher = "fresher"
    mid = "mid"
    senior = "senior"
    all_levels = "all_levels"


class QuestionCategory(str, Enum):
    """High-level categories that group screening questions by purpose."""
    introduction = "introduction"
    education = "education"
    experience = "experience"
    skills = "skills"
    location = "location"
    salary = "salary"
    notice_period = "notice_period"
    qe_specific = "qe_specific"


class ScreeningQuestion(BaseModel):
    """
    Represents a single HR screening question.

    Each question carries metadata used by downstream engines:
    - expected_keywords   → answer understanding engine (Day 25)
    - importance          → scoring engine (Day 26)
    - follow_up_trigger / follow_up_question → conversation engine (Days 29-30)
    - applicable_levels   → level-based question filtering
    - multilingual        → future Hindi/Malayalam support
    """

    question_id: str = Field(..., description="Unique identifier, e.g. Q_INTRO_001")
    question_text: str = Field(..., description="The question as spoken or displayed to the candidate")
    category: QuestionCategory = Field(..., description="High-level category this question belongs to")
    answer_type: AnswerType = Field(..., description="Expected format of the candidate's answer")
    mandatory: bool = Field(..., description="Whether this question must be asked in every screening")
    importance: int = Field(..., ge=1, le=5, description="Scoring weight: 1=low importance, 5=critical")
    applicable_levels: List[RoleLevel] = Field(
        default_factory=lambda: [RoleLevel.all_levels],
        description="Role levels this question applies to"
    )
    expected_keywords: List[str] = Field(
        default_factory=list,
        description="Domain keywords the answer understanding engine checks for"
    )
    follow_up_trigger: str = Field(
        default="",
        description="Condition that causes the conversation engine to ask the follow-up"
    )
    follow_up_question: str = Field(
        default="",
        description="Follow-up question asked when the trigger condition is met"
    )
    multilingual: dict = Field(
        default_factory=dict,
        description="Future translations keyed by language code, e.g. {'hi': '...', 'ml': '...'}"
    )
    notes: str = Field(default="", description="Internal notes for question designers or reviewers")


class QuestionBank(BaseModel):
    """
    Full question bank for a specific job posting, stored in Redis as question_bank:{job_id}.

    Contains all ScreeningQuestion objects plus metadata used by the
    conversation engine to select, order, and score questions at runtime.
    """

    job_id: str = Field(..., description="Unique job identifier, matches Redis key suffix")
    job_title: str = Field(..., description="Human-readable job title")
    domain: str = Field(..., description="QE sub-domain: automotive_manufacturing, food_safety, pharma")
    total_questions: int = Field(..., description="Total number of questions in this bank")
    categories: List[str] = Field(..., description="Unique categories present in this bank")
    questions: List[ScreeningQuestion] = Field(..., description="Ordered list of all screening questions")
    created_at: str = Field(..., description="ISO 8601 UTC timestamp of when this bank was created")
    version: str = Field(default="1.0.0", description="Schema version for forward compatibility")
