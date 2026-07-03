"""
interview_ai/aptitude_models.py

Pydantic v2 models for the Aptitude AI capability (logical reasoning,
situational judgment, and analytical thinking evaluation).
Part of Zecpath AI — Day 38, Sprint 4.

CRITICAL: No imports from screening_ai, ats_engine, or scoring — this
module is fully self-contained, consistent with the rest of interview_ai.
Aptitude scoring is NOT wired into hr_scoring_engine.py; cross-round
aggregation with HR scores is a future Decision Service concern.
"""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

from utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class AptitudeCategory(str, Enum):
    """
    Fine-grained categories that group aptitude questions by evaluation
    focus.

    Duplicated independently of interview_models.InterviewQuestionCategory
    despite conceptual overlap — interview_ai submodules do not share
    enums by import, per project convention (see DAY38_DECISIONS.md).
    """

    logical_reasoning = "logical_reasoning"
    situational_judgment = "situational_judgment"
    analytical_thinking = "analytical_thinking"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class AptitudeQuestion(BaseModel):
    """
    Represents a single aptitude evaluation question.

    situational_judgment questions carry a `scenario_type` that links
    them to a scenario pattern key used by scenario_evaluator.py for
    ratio-based pattern matching against the candidate's answer.
    """

    question_id: str = Field(
        ..., description="Unique identifier, e.g. AQ_LOGIC_001"
    )
    category: AptitudeCategory = Field(
        ..., description="Aptitude category this question belongs to"
    )
    text: str = Field(
        ..., description="The question as presented to the candidate"
    )
    scenario_type: Optional[str] = Field(
        default=None,
        description=(
            "Links situational_judgment questions to a scenario pattern "
            "key in scenario_evaluator.SCENARIO_PATTERNS. None for "
            "logical_reasoning and analytical_thinking questions."
        ),
    )


class AptitudeQuestionBank(BaseModel):
    """
    Full aptitude question bank for a specific job posting.

    File-based storage only for now (data/aptitude_questions.json).
    Redis persistence is a deferred Sprint 3 backlog item — see
    DAY38_DECISIONS.md.
    """

    job_id: str = Field(
        ..., description="Unique job identifier this bank applies to"
    )
    questions: List[AptitudeQuestion] = Field(
        ..., description="All aptitude questions in this bank"
    )
    version: str = Field(
        default="1.0.0",
        description="Schema version for forward compatibility",
    )


class AptitudeScoreBreakdown(BaseModel):
    """Per-dimension breakdown of aptitude sub-scores.

    All sub-scores represent a normalised 0.0-1.0 ratio-based range,
    computed by aptitude_scoring.py.
    """

    structure: float = Field(
        ge=0, le=1, description="Reasoning-structure sub-score (0.0-1.0)."
    )
    problem_solving: float = Field(
        ge=0, le=1, description="Problem-solving marker sub-score (0.0-1.0)."
    )
    decision_quality: float = Field(
        ge=0, le=1, description="Decision-quality marker sub-score (0.0-1.0)."
    )


class ScenarioEvaluation(BaseModel):
    """
    Result of matching a candidate's answer against a scenario's expected
    behavioral pattern keywords.

    Produced by scenario_evaluator.evaluate_scenario() using ratio-based
    matching (matched_patterns / total_patterns), not binary tiers.
    """

    scenario_type: str = Field(
        ..., description="The scenario pattern key that was evaluated"
    )
    match_ratio: float = Field(
        ge=0, le=1, description="matched_patterns / total_patterns, rounded 4dp"
    )
    matched_patterns: List[str] = Field(
        ..., description="Pattern keywords found in the candidate's answer"
    )
    total_patterns: int = Field(
        ..., description="Total number of pattern keywords for this scenario_type"
    )


class AptitudeScore(BaseModel):
    """
    Top-level aptitude score for a single candidate answer.

    Captures the aggregated 0-100 score, the per-dimension breakdown, an
    optional scenario evaluation (present only when scenario_type was
    supplied), and the total word count of the evaluated text.
    """

    aptitude_score: float = Field(
        ge=0, le=100, description="Aggregated aptitude score (0.0-100.0), rounded to 2 d.p."
    )
    breakdown: AptitudeScoreBreakdown = Field(
        description="Per-dimension scores used to compute the final score."
    )
    scenario_evaluation: Optional[ScenarioEvaluation] = Field(
        default=None,
        description="Scenario pattern-match result, present only when scenario_type was provided.",
    )
    word_count: int = Field(description="Total word count of the evaluated answer text.")
