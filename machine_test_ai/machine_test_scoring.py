"""
machine_test_ai/machine_test_scoring.py

Day 50 machine test scoring engine. Combines four sub-scores
(correctness, code_quality, efficiency, problem_solving) into a
task_score, blends that with a time_score into a final_score, and maps
the result to a decision label.

DOMAIN-DEVIATION NOTICE: This module intentionally models a generic
software-engineering machine test track rather than the platform's
established QE domain (see technical_ai/), per explicit direction --
see machine_test_ai/DAY50_DECISIONS.md.

CALLER-SUPPLIED-VS-DERIVED DISTINCTION: This module contains NO code
execution engine, NO sandboxing, NO test-runner, and NO
static-analysis/linting logic. correctness, efficiency, and
problem_solving are real deterministic ratios computed from
caller-supplied raw counts/measurements. code_quality alone is a
fully opaque caller-supplied judgment score, passed through unchanged,
since no execution engine or static-analysis tooling exists in this
module's scope.

MODULE ISOLATION: Zero imports from interview_ai/, technical_ai/,
screening_ai/, ats_engine/, scoring/, decision_ai/,
visual_behavior_ai/, or integrity_ai/. Only imports from
machine_test_ai.machine_test_models (intra-module, permitted). No
constant or helper is imported cross-module; anything shared-looking
is duplicated by value.

Deliberately NOT wired into decision_ai/ or any other scoring system
this day -- same "deliberately unwired, single day's scope" precedent
already established for visual_behavior_ai/ (Day 48) and integrity_ai/
(Day 49).

DETERMINISM RULE (non-negotiable, project-wide): no use of the
`random` module anywhere in this file.
"""

from utils.logger import get_logger

from machine_test_ai.machine_test_models import (
    MachineTestScore,
    MachineTestScoreBreakdown,
    MachineTestSubmission,
)

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Weights
# ---------------------------------------------------------------------------

TASK_SCORE_WEIGHTS: dict[str, float] = {
    "correctness": 0.40,
    "code_quality": 0.30,
    "efficiency": 0.15,
    "problem_solving": 0.15,
}
assert sum(TASK_SCORE_WEIGHTS.values()) == 1.0

# EXPLICIT, STATED weight split -- unlike the reviewed manager sample,
# which blended task_score and time_score at an unexplained 80/20
# ratio with no documented rationale. See machine_test_ai/
# DAY50_DECISIONS.md.
FINAL_SCORE_WEIGHTS: dict[str, float] = {
    "task_score": 0.75,
    "time_score": 0.25,
}
assert sum(FINAL_SCORE_WEIGHTS.values()) == 1.0

# ---------------------------------------------------------------------------
# Normalization caps
# ---------------------------------------------------------------------------

# The attempts count at which problem_solving bottoms out at 0.0 --
# same normalization-cap concept as integrity_ai.EVENT_CAPS, duplicated
# by value, not imported.
ATTEMPTS_CAP: int = 5


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _capped_ratio(value: float, cap: float, invert: bool = False) -> float:
    """Normalize a raw value into a [0.0, 1.0] ratio against a cap.

    Generalized version of integrity_ai's _normalize_signal (duplicated
    by value, not imported), with two formula branches:

        if invert is False: round(min(value / cap, 1.0), 4)
        if invert is True:  round(max(1.0 - (value / cap), 0.0), 4)

    The non-inverted branch is used where a higher raw value means a
    higher score (capped at 1.0 once value reaches cap). The inverted
    branch is used where a higher raw value means a lower score (the
    score bottoms out at 0.0 once value reaches cap).

    Args:
        value: Raw caller-supplied value to normalize.
        cap: Normalization denominator.
        invert: If True, use the inverted (higher value = lower score)
            formula branch. Defaults to False.

    Returns:
        A float in [0.0, 1.0] rounded to 4 decimal places.
    """
    if invert:
        result = round(max(1.0 - (value / cap), 0.0), 4)
    else:
        result = round(min(value / cap, 1.0), 4)
    logger.debug(
        "_capped_ratio(value=%r, cap=%r, invert=%r) -> %.4f",
        value,
        cap,
        invert,
        result,
    )
    return result


# ---------------------------------------------------------------------------
# Public scoring functions
# ---------------------------------------------------------------------------


def score_correctness(submission: MachineTestSubmission) -> float:
    """Score correctness as the ratio of passed tests to total tests.

    A real ratio, not a placeholder -- both inputs are concrete counts.

    Args:
        submission: The machine test submission.

    Returns:
        round(passed_test_count / total_test_count, 4), clamped to
        [0.0, 1.0].
    """
    ratio = submission.passed_test_count / submission.total_test_count
    result = round(min(max(ratio, 0.0), 1.0), 4)
    logger.debug("score_correctness -> %.4f", result)
    return result


def score_efficiency(submission: MachineTestSubmission) -> float:
    """Score efficiency by comparing runtime against the task's baseline.

    Runtime at or below baseline scores 1.0; runtime above baseline
    degrades proportionally. runtime_seconds == 0 is treated
    explicitly as a perfect efficiency score of 1.0, avoiding division
    by zero.

    Args:
        submission: The machine test submission.

    Returns:
        round(min(runtime_baseline_seconds / max(runtime_seconds,
        0.0001), 1.0), 4).
    """
    if submission.runtime_seconds == 0:
        logger.debug(
            "score_efficiency: runtime_seconds == 0, returning perfect "
            "efficiency score of 1.0 explicitly."
        )
        return 1.0

    result = round(
        min(
            submission.runtime_baseline_seconds
            / max(submission.runtime_seconds, 0.0001),
            1.0,
        ),
        4,
    )
    logger.debug("score_efficiency -> %.4f", result)
    return result


def score_problem_solving(submission: MachineTestSubmission) -> float:
    """Score problem solving based on number of attempts taken.

    Fewer attempts = higher score.

    Args:
        submission: The machine test submission.

    Returns:
        _capped_ratio(submission.attempts, ATTEMPTS_CAP, invert=True).
    """
    result = _capped_ratio(submission.attempts, ATTEMPTS_CAP, invert=True)
    logger.debug("score_problem_solving -> %.4f", result)
    return result


def score_time(submission: MachineTestSubmission) -> float:
    """Score time taken against the time limit, on a 0-100 scale.

    Unlike the other three sub-scores, which stay 0-1 until the final
    aggregation step, this produces the 0-100 scale time_score
    directly.

    Args:
        submission: The machine test submission.

    Returns:
        _capped_ratio(time_taken_seconds, time_limit_seconds,
        invert=True) * 100, rounded to 2 d.p.
    """
    ratio = _capped_ratio(
        submission.time_taken_seconds, submission.time_limit_seconds, invert=True
    )
    result = round(ratio * 100, 2)
    logger.debug("score_time -> %.2f", result)
    return result


def get_machine_test_decision(score: float) -> str:
    """Map a final_score to a practical-fit decision label.

    Independently scoped thresholds and wording (not reusing 75/55
    from HR/technical) -- this wording is deliberately distinct from
    every other decision-band label family on the platform, per the
    project's ongoing mitigation of its known multi-label-divergence
    concern.

    Args:
        score: Aggregate final score (0.0-100.0).

    Returns:
        "Strong Practical Fit" if score >= 70, "Moderate Practical
        Fit" if score >= 45, otherwise "Weak Practical Fit".
    """
    if score >= 70:
        return "Strong Practical Fit"
    if score >= 45:
        return "Moderate Practical Fit"
    return "Weak Practical Fit"


def calculate_machine_test_score(submission: dict) -> MachineTestScore:
    """Score a full machine test submission from a raw input dict.

    VALIDATION APPROACH (deliberate deviation from technical_ai/
    integrity_ai's manual pre-check pattern): the MachineTestSubmission
    model is constructed directly from `submission`, letting Pydantic
    raise its own ValidationError for missing/invalid keys. No
    separate manual missing-key check is added here, because every
    field on MachineTestSubmission already has an explicit Field
    constraint and is unconditionally required with no optional/
    None-tolerant semantics -- unlike the prior two modules, this
    module has no fields where a manual pre-check would add clarity
    Pydantic's own error does not already provide. See
    machine_test_ai/DAY50_DECISIONS.md.

    Args:
        submission: Raw dict of the seven MachineTestSubmission fields.

    Returns:
        A fully populated MachineTestScore.

    Raises:
        pydantic.ValidationError: If any required field is missing or
            fails its Field constraint.
    """
    logger.debug("calculate_machine_test_score called with submission=%r", submission)

    submission_model = MachineTestSubmission(**submission)

    correctness = score_correctness(submission_model)
    code_quality = submission_model.code_quality
    efficiency = score_efficiency(submission_model)
    problem_solving = score_problem_solving(submission_model)

    task_score = round(
        (
            correctness * TASK_SCORE_WEIGHTS["correctness"]
            + code_quality * TASK_SCORE_WEIGHTS["code_quality"]
            + efficiency * TASK_SCORE_WEIGHTS["efficiency"]
            + problem_solving * TASK_SCORE_WEIGHTS["problem_solving"]
        )
        * 100,
        2,
    )

    time_score = score_time(submission_model)

    final_score = round(
        task_score * FINAL_SCORE_WEIGHTS["task_score"]
        + time_score * FINAL_SCORE_WEIGHTS["time_score"],
        2,
    )

    decision = get_machine_test_decision(final_score)

    breakdown = MachineTestScoreBreakdown(
        correctness=correctness,
        code_quality=code_quality,
        efficiency=efficiency,
        problem_solving=problem_solving,
    )

    logger.info(
        "calculate_machine_test_score task_score=%.2f time_score=%.2f "
        "final_score=%.2f decision=%s",
        task_score,
        time_score,
        final_score,
        decision,
    )

    return MachineTestScore(
        task_score=task_score,
        time_score=time_score,
        final_score=final_score,
        decision=decision,
        breakdown=breakdown,
        submission=submission_model,
    )
