"""Tests for screening_ai.conversation_flow.ConversationStateMachine."""

import pytest

from screening_ai.conversation_flow import ConversationStateMachine


def _make_question(
    question_id: str = "q1",
    question: str = "Tell me about yourself",
    follow_up_question: str | None = None,
    follow_up_trigger: bool = False,
    mandatory: bool = True,
    importance: int = 3,
) -> dict:
    """Build a question dict matching the Day 22 question bank schema."""
    return {
        "question_id": question_id,
        "question": question,
        "follow_up_question": follow_up_question,
        "follow_up_trigger": follow_up_trigger,
        "mandatory": mandatory,
        "importance": importance,
    }


def test_get_current_question() -> None:
    """get_current_question returns the first question on a fresh machine."""
    questions = [_make_question(question_id="q1"), _make_question(question_id="q2")]
    machine = ConversationStateMachine(questions)

    current = machine.get_current_question()

    assert current is not None
    assert current["question_id"] == "q1"


def test_valid_response_advances() -> None:
    """A valid response returns 'next' and advances current_index."""
    questions = [_make_question(question_id="q1"), _make_question(question_id="q2")]
    machine = ConversationStateMachine(questions)

    result = machine.handle_response("processed", "This is a valid answer")

    assert result == "next"
    assert machine.current_index == 1


def test_silence_triggers_retry() -> None:
    """A silence_detected status returns 'retry' without advancing."""
    questions = [_make_question(question_id="q1")]
    machine = ConversationStateMachine(questions)

    result = machine.handle_response("silence_detected", "")

    assert result == "retry"
    assert machine.current_index == 0


def test_retry_limit_skips() -> None:
    """Exceeding MAX_RETRIES on one question returns 'skip' and advances."""
    questions = [_make_question(question_id="q1"), _make_question(question_id="q2")]
    machine = ConversationStateMachine(questions)

    # MAX_RETRIES == 2, so attempts 1 and 2 should retry; attempt 3
    # exhausts the budget and skips ahead.
    machine.handle_response("silence_detected", "")
    machine.handle_response("silence_detected", "")
    result = machine.handle_response("silence_detected", "")

    assert result == "skip"
    assert machine.current_index == 1


def test_follow_up_trigger() -> None:
    """A valid response on a follow_up_trigger question returns 'follow_up'."""
    questions = [_make_question(question_id="q1", follow_up_trigger=True)]
    machine = ConversationStateMachine(questions)

    result = machine.handle_response("processed", "This is a valid answer")

    assert result == "follow_up"


def test_record_exchange() -> None:
    """A valid response appends exactly one clean entry to history."""
    questions = [_make_question(question_id="q1"), _make_question(question_id="q2")]
    machine = ConversationStateMachine(questions)

    machine.handle_response("processed", "This is a valid answer")

    assert len(machine.history) == 1
    assert machine.history[0]["question_id"] == "q1"


def test_invalid_stt_status_raises() -> None:
    """record_exchange raises ValueError for an unrecognized stt_status."""
    questions = [_make_question(question_id="q1")]
    machine = ConversationStateMachine(questions)

    with pytest.raises(ValueError):
        machine.record_exchange("q1", "This is a valid answer", "unknown_status")


def test_completion() -> None:
    """A single-question machine completes after one valid response."""
    questions = [_make_question(question_id="q1")]
    machine = ConversationStateMachine(questions)

    machine.handle_response("processed", "This is a valid answer")

    assert machine.is_complete() is True


# ---------------------------------------------------------------------------
# Day 31 additions — noise / language-mix detection
# ---------------------------------------------------------------------------


def test_detect_issue_noise() -> None:
    """detect_issue should return 'noise' for stt_status='noise_detected'."""
    questions = [_make_question(question_id="q1")]
    machine = ConversationStateMachine(questions)

    result = machine.detect_issue("noise_detected", "some answer text here")

    assert result == "noise", f"Expected 'noise', got {result!r}"


def test_detect_issue_language_mixed() -> None:
    """detect_issue should return 'language_mixed' for stt_status='language_mixed_detected'."""
    questions = [_make_question(question_id="q1")]
    machine = ConversationStateMachine(questions)

    result = machine.detect_issue("language_mixed_detected", "some answer text here")

    assert result == "language_mixed", f"Expected 'language_mixed', got {result!r}"
