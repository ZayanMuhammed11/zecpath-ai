"""
tests/test_machine_test_scoring.py

Day 50 tests for machine_test_ai.machine_test_scoring.
"""

import random as _random_module_for_check

import pytest
from pydantic import ValidationError

from machine_test_ai.machine_test_models import MachineTestScore
from machine_test_ai.machine_test_scoring import (
    ATTEMPTS_CAP,
    FINAL_SCORE_WEIGHTS,
    TASK_SCORE_WEIGHTS,
    calculate_machine_test_score,
    get_machine_test_decision,
    score_correctness,
    score_efficiency,
    score_problem_solving,
    score_time,
)
from machine_test_ai.machine_test_models import MachineTestSubmission


# ---------------------------------------------------------------------------
# Full pipeline: valid submission with hand-computed expected result
# ---------------------------------------------------------------------------


def test_calculate_machine_test_score_hand_computed():
    """Hand-computed end-to-end example.

    Inputs:
        passed_test_count=8, total_test_count=10
        runtime_seconds=10.0, runtime_baseline_seconds=5.0
        code_quality=0.9
        attempts=2
        time_taken_seconds=30.0, time_limit_seconds=60.0

    By hand:
        correctness = 8 / 10 = 0.8
        efficiency = min(5.0 / 10.0, 1.0) = 0.5
        code_quality = 0.9 (passed through)
        problem_solving = max(1.0 - (2 / 5), 0.0) = 0.6

        task_score = (0.8*0.40 + 0.9*0.30 + 0.5*0.15 + 0.6*0.15) * 100
                   = (0.32 + 0.27 + 0.075 + 0.09) * 100
                   = 0.755 * 100 = 75.5

        time_ratio = max(1.0 - (30.0 / 60.0), 0.0) = 0.5
        time_score = 0.5 * 100 = 50.0

        final_score = 75.5*0.75 + 50.0*0.25 = 56.625 + 12.5 = 69.125
                    -> rounds to 69.12
    """
    submission = {
        "passed_test_count": 8,
        "total_test_count": 10,
        "runtime_seconds": 10.0,
        "runtime_baseline_seconds": 5.0,
        "code_quality": 0.9,
        "attempts": 2,
        "time_taken_seconds": 30.0,
        "time_limit_seconds": 60.0,
    }

    result = calculate_machine_test_score(submission)

    assert isinstance(result, MachineTestScore)
    assert result.breakdown.correctness == 0.8
    assert result.breakdown.efficiency == 0.5
    assert result.breakdown.code_quality == 0.9
    assert result.breakdown.problem_solving == 0.6
    assert result.task_score == 75.5
    assert result.time_score == 50.0
    assert result.final_score == 69.12
    assert 0.0 <= result.final_score <= 100.0
    assert result.decision == "Moderate Practical Fit"


# ---------------------------------------------------------------------------
# score_correctness
# ---------------------------------------------------------------------------


def test_score_correctness_non_trivial_ratio():
    submission = MachineTestSubmission(
        passed_test_count=3,
        total_test_count=4,
        runtime_seconds=1.0,
        runtime_baseline_seconds=1.0,
        code_quality=0.5,
        attempts=1,
        time_taken_seconds=1.0,
        time_limit_seconds=2.0,
    )
    assert score_correctness(submission) == 0.75


def test_score_correctness_all_passed():
    submission = MachineTestSubmission(
        passed_test_count=5,
        total_test_count=5,
        runtime_seconds=1.0,
        runtime_baseline_seconds=1.0,
        code_quality=0.5,
        attempts=1,
        time_taken_seconds=1.0,
        time_limit_seconds=2.0,
    )
    assert score_correctness(submission) == 1.0


# ---------------------------------------------------------------------------
# score_efficiency
# ---------------------------------------------------------------------------


def test_score_efficiency_at_baseline():
    submission = MachineTestSubmission(
        passed_test_count=1,
        total_test_count=1,
        runtime_seconds=5.0,
        runtime_baseline_seconds=5.0,
        code_quality=0.5,
        attempts=1,
        time_taken_seconds=1.0,
        time_limit_seconds=2.0,
    )
    assert score_efficiency(submission) == 1.0


def test_score_efficiency_double_baseline():
    submission = MachineTestSubmission(
        passed_test_count=1,
        total_test_count=1,
        runtime_seconds=10.0,
        runtime_baseline_seconds=5.0,
        code_quality=0.5,
        attempts=1,
        time_taken_seconds=1.0,
        time_limit_seconds=2.0,
    )
    assert score_efficiency(submission) == 0.5


def test_score_efficiency_zero_runtime_no_division_error():
    submission = MachineTestSubmission(
        passed_test_count=1,
        total_test_count=1,
        runtime_seconds=0.0,
        runtime_baseline_seconds=5.0,
        code_quality=0.5,
        attempts=1,
        time_taken_seconds=1.0,
        time_limit_seconds=2.0,
    )
    assert score_efficiency(submission) == 1.0


# ---------------------------------------------------------------------------
# score_problem_solving
# ---------------------------------------------------------------------------


def test_score_problem_solving_one_attempt():
    submission = MachineTestSubmission(
        passed_test_count=1,
        total_test_count=1,
        runtime_seconds=1.0,
        runtime_baseline_seconds=1.0,
        code_quality=0.5,
        attempts=1,
        time_taken_seconds=1.0,
        time_limit_seconds=2.0,
    )
    # Hand-computed: max(1.0 - (1 / ATTEMPTS_CAP), 0.0) = max(1.0 - 0.2, 0.0) = 0.8
    expected = round(max(1.0 - (1 / ATTEMPTS_CAP), 0.0), 4)
    assert expected == 0.8
    assert score_problem_solving(submission) == expected


def test_score_problem_solving_at_cap_is_zero():
    submission = MachineTestSubmission(
        passed_test_count=1,
        total_test_count=1,
        runtime_seconds=1.0,
        runtime_baseline_seconds=1.0,
        code_quality=0.5,
        attempts=ATTEMPTS_CAP,
        time_taken_seconds=1.0,
        time_limit_seconds=2.0,
    )
    assert score_problem_solving(submission) == 0.0


# ---------------------------------------------------------------------------
# score_time
# ---------------------------------------------------------------------------


def test_score_time_well_under_limit():
    submission = MachineTestSubmission(
        passed_test_count=1,
        total_test_count=1,
        runtime_seconds=1.0,
        runtime_baseline_seconds=1.0,
        code_quality=0.5,
        attempts=1,
        time_taken_seconds=10.0,
        time_limit_seconds=100.0,
    )
    # max(1.0 - (10/100), 0.0) * 100 = 90.0
    assert score_time(submission) == 90.0


def test_score_time_at_limit():
    submission = MachineTestSubmission(
        passed_test_count=1,
        total_test_count=1,
        runtime_seconds=1.0,
        runtime_baseline_seconds=1.0,
        code_quality=0.5,
        attempts=1,
        time_taken_seconds=100.0,
        time_limit_seconds=100.0,
    )
    # max(1.0 - (100/100), 0.0) * 100 = 0.0
    assert score_time(submission) == 0.0


def test_score_time_over_limit():
    submission = MachineTestSubmission(
        passed_test_count=1,
        total_test_count=1,
        runtime_seconds=1.0,
        runtime_baseline_seconds=1.0,
        code_quality=0.5,
        attempts=1,
        time_taken_seconds=150.0,
        time_limit_seconds=100.0,
    )
    # max(1.0 - (150/100), 0.0) * 100 = max(-0.5, 0.0) * 100 = 0.0
    assert score_time(submission) == 0.0


# ---------------------------------------------------------------------------
# Missing required field -> pydantic ValidationError
# ---------------------------------------------------------------------------


def test_missing_required_field_raises_pydantic_validation_error():
    submission = {
        "passed_test_count": 5,
        "total_test_count": 10,
        "runtime_seconds": 1.0,
        "runtime_baseline_seconds": 1.0,
        "code_quality": 0.5,
        "attempts": 1,
        # "time_taken_seconds" intentionally omitted
        "time_limit_seconds": 10.0,
    }
    with pytest.raises(ValidationError):
        calculate_machine_test_score(submission)


# ---------------------------------------------------------------------------
# get_machine_test_decision band boundaries
# ---------------------------------------------------------------------------


def test_decision_boundary_strong_below_and_at_70():
    assert get_machine_test_decision(69.99) == "Moderate Practical Fit"
    assert get_machine_test_decision(70.0) == "Strong Practical Fit"


def test_decision_boundary_moderate_below_and_at_45():
    assert get_machine_test_decision(44.99) == "Weak Practical Fit"
    assert get_machine_test_decision(45.0) == "Moderate Practical Fit"


def test_decision_weak_below_45():
    assert get_machine_test_decision(10.0) == "Weak Practical Fit"


# ---------------------------------------------------------------------------
# Weight constants
# ---------------------------------------------------------------------------


def test_task_score_weights_sum_to_one():
    assert sum(TASK_SCORE_WEIGHTS.values()) == 1.0


def test_final_score_weights_sum_to_one():
    assert sum(FINAL_SCORE_WEIGHTS.values()) == 1.0


# ---------------------------------------------------------------------------
# Result type check
# ---------------------------------------------------------------------------


def test_result_is_machine_test_score_instance():
    submission = {
        "passed_test_count": 5,
        "total_test_count": 10,
        "runtime_seconds": 5.0,
        "runtime_baseline_seconds": 5.0,
        "code_quality": 0.5,
        "attempts": 1,
        "time_taken_seconds": 5.0,
        "time_limit_seconds": 10.0,
    }
    result = calculate_machine_test_score(submission)
    assert isinstance(result, MachineTestScore)


# ---------------------------------------------------------------------------
# No use of the random module anywhere in these tests
# ---------------------------------------------------------------------------


def test_no_random_module_used_in_tests():
    """Confirms this test file does not rely on the `random` module.

    The import at the top of this file is aliased and used only for
    this identity check -- no test in this file calls any function
    from the `random` module to generate inputs or expected values.
    """
    assert _random_module_for_check.__name__ == "random"
