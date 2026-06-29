"""
tests/test_followup_engine.py

Pytest tests for interview_ai/followup_engine.py — Day 34, Sprint 4.

No Redis or external dependencies — all tests are fully self-contained.
A local make_question() helper constructs minimal valid InterviewQuestion
instances; a make_state() helper constructs minimal valid InterviewState
instances. Both follow the pattern established by Day 33's test helpers.
"""

import pytest

from interview_ai.interview_models import (
    InterviewPhase,
    InterviewQuestion,
    InterviewQuestionCategory,
    InterviewState,
    RoleLevel,
    RoleType,
)
from interview_ai.followup_models import (
    AnswerQuality,
    FollowUpAction,
    MAX_FOLLOWUP_ATTEMPTS,
)
from interview_ai.followup_engine import (
    build_followup_result,
    decide_followup_action,
    generate_followup_text,
    is_repeated_question,
    record_question_asked,
)


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def make_question(
    question_id: str = "IQ_TEST_001",
    text: str = "Tell me about yourself.",
    category: InterviewQuestionCategory = InterviewQuestionCategory.teamwork_culture_fit,
    phase: InterviewPhase = InterviewPhase.core_hr,
    follow_up_eligible: bool = True,
    order: int = 1,
) -> InterviewQuestion:
    """Build a minimal valid InterviewQuestion for use in tests."""
    return InterviewQuestion(
        question_id=question_id,
        text=text,
        category=category,
        phase=phase,
        follow_up_eligible=follow_up_eligible,
        order=order,
    )


def make_state(
    questions_asked: list[str] | None = None,
) -> InterviewState:
    """Build a minimal valid InterviewState for use in tests."""
    return InterviewState(
        candidate_id="CAND_001",
        job_id="JOB_001",
        current_phase=InterviewPhase.core_hr,
        role_level=RoleLevel.mid,
        role_type=RoleType.non_technical,
        questions_asked=questions_asked or [],
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "quality, expected_action",
    [
        (AnswerQuality.good, FollowUpAction.none),
        (AnswerQuality.basic, FollowUpAction.request_example),
        (AnswerQuality.too_short, FollowUpAction.request_elaboration),
        (AnswerQuality.off_topic, FollowUpAction.request_clarification),
        (AnswerQuality.no_answer, FollowUpAction.request_clarification),
    ],
)
def test_decide_action_for_each_quality_value(
    quality: AnswerQuality,
    expected_action: FollowUpAction,
) -> None:
    """All 5 AnswerQuality values map to their correct FollowUpAction per the decision table."""
    question = make_question()
    result = decide_followup_action(question, quality, {})
    assert result == expected_action


def test_decide_action_returns_none_when_not_eligible() -> None:
    """follow_up_eligible=False forces FollowUpAction.none regardless of quality."""
    question = make_question(follow_up_eligible=False)
    # Use a quality that would normally produce a non-none action to prove override fires
    result = decide_followup_action(question, AnswerQuality.too_short, {})
    assert result == FollowUpAction.none


def test_decide_action_returns_none_at_max_attempts() -> None:
    """Reaching MAX_FOLLOWUP_ATTEMPTS in the attempts dict forces FollowUpAction.none."""
    question = make_question()
    attempts = {question.question_id: MAX_FOLLOWUP_ATTEMPTS}
    # Use a quality that would normally produce a non-none action
    result = decide_followup_action(question, AnswerQuality.no_answer, attempts)
    assert result == FollowUpAction.none


def test_decide_action_allows_followup_below_max_attempts() -> None:
    """One attempt below the cap still fires the quality-based action (override does not trigger)."""
    question = make_question()
    attempts = {question.question_id: MAX_FOLLOWUP_ATTEMPTS - 1}
    result = decide_followup_action(question, AnswerQuality.too_short, attempts)
    assert result == FollowUpAction.request_elaboration


def test_generate_followup_text_returns_none_for_none_action() -> None:
    """generate_followup_text returns None when action is FollowUpAction.none."""
    question = make_question()
    result = generate_followup_text(question, FollowUpAction.none)
    assert result is None


def test_generate_followup_text_is_deterministic() -> None:
    """Two calls with identical question and action produce identical output text."""
    question = make_question(text="Describe a challenge you overcame.")
    action = FollowUpAction.request_elaboration

    first = generate_followup_text(question, action)
    second = generate_followup_text(question, action)

    assert first is not None, "Expected a non-None string for request_elaboration"
    assert first == second


def test_is_repeated_question() -> None:
    """is_repeated_question returns True for a known id and False for an unknown one."""
    state = make_state(questions_asked=["Q1"])
    assert is_repeated_question(state, "Q1") is True
    assert is_repeated_question(state, "Q2") is False


def test_record_question_asked_is_idempotent() -> None:
    """
    Calling record_question_asked twice with the same id does not duplicate the entry,
    and the original state object is not mutated by either call.
    """
    original_state = make_state(questions_asked=[])

    first_update = record_question_asked(original_state, "Q1")
    second_update = record_question_asked(first_update, "Q1")

    # id appears exactly once in the final result
    assert second_update.questions_asked.count("Q1") == 1

    # original state was not mutated
    assert "Q1" not in original_state.questions_asked
