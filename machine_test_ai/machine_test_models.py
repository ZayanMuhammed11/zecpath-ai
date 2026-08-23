"""
machine_test_ai/machine_test_models.py

Day 50 machine test scoring models.

DOMAIN-DEVIATION NOTICE: This module intentionally models a generic
software-engineering machine test track rather than the platform's
established QE domain (see technical_ai/), per explicit direction --
see machine_test_ai/DAY50_DECISIONS.md.

CALLER-SUPPLIED-VS-DERIVED DISTINCTION: This module contains NO code
execution engine, NO sandboxing, NO test-runner, and NO
static-analysis/linting logic. Every numeric input to every function
in this module is either (a) a raw caller-supplied count/measurement
that this module normalizes with real, transparent arithmetic, or (b)
a fully opaque caller-supplied judgment score for the one dimension
(code_quality) that cannot be deterministically derived without
execution tooling or an LLM/human reviewer, neither of which exists in
this module's scope. These two categories are never blurred together:
passed_test_count/total_test_count, runtime_seconds/
runtime_baseline_seconds, attempts, and time_taken_seconds/
time_limit_seconds are all category (a); code_quality alone is
category (b).

MODULE ISOLATION: Zero imports from interview_ai/, technical_ai/,
screening_ai/, ats_engine/, scoring/, decision_ai/,
visual_behavior_ai/, or integrity_ai/. Pydantic v2 models only, no
scoring logic in this file.
"""

from pydantic import BaseModel, Field


class MachineTestSubmission(BaseModel):
    """Raw caller-supplied inputs for a single machine test submission.

    One field per real measurable quantity, plus one opaque
    caller-supplied judgment score (code_quality). No field in this
    model is derived or computed here -- this is a pure data
    container.
    """

    passed_test_count: int = Field(ge=0)
    total_test_count: int = Field(
        ge=1,
        description=(
            "Must be >= 1; a task with zero total tests is not a valid "
            "submission."
        ),
    )
    runtime_seconds: float = Field(ge=0)
    runtime_baseline_seconds: float = Field(
        gt=0,
        description=(
            "Caller-supplied reference runtime for this specific task; "
            "used only to normalize runtime_seconds, not a universal "
            "constant."
        ),
    )
    code_quality: float = Field(
        ge=0,
        le=1,
        description=(
            "OPAQUE CALLER-SUPPLIED judgment score for code quality. "
            "This module performs no static analysis or execution -- "
            "this value must be supplied by an external reviewer, "
            "linter, or LLM. Mirrors the caller-supplied `accuracy` "
            "pattern in technical_ai.technical_scoring_engine."
        ),
    )
    attempts: int = Field(
        ge=1,
        description="Number of attempts taken to reach the submitted solution.",
    )
    time_taken_seconds: float = Field(ge=0)
    time_limit_seconds: float = Field(gt=0)


class MachineTestScoreBreakdown(BaseModel):
    """Per-dimension sub-scores that compose task_score."""

    correctness: float = Field(ge=0, le=1)
    code_quality: float = Field(ge=0, le=1)
    efficiency: float = Field(ge=0, le=1)
    problem_solving: float = Field(ge=0, le=1)


class MachineTestScore(BaseModel):
    """Fully populated machine test scoring result."""

    task_score: float = Field(
        ge=0,
        le=100,
        description=(
            "Weighted composite of correctness, code_quality, "
            "efficiency, problem_solving, on a 0-100 scale."
        ),
    )
    time_score: float = Field(
        ge=0,
        le=100,
        description="Normalized time-taken-vs-limit score on a 0-100 scale.",
    )
    final_score: float = Field(
        ge=0,
        le=100,
        description=(
            "Blend of task_score and final weighting per "
            "FINAL_SCORE_WEIGHTS."
        ),
    )
    decision: str
    breakdown: MachineTestScoreBreakdown
    submission: MachineTestSubmission
