"""
tests/test_aptitude_question_bank.py

Pytest test suite for interview_ai/aptitude_question_bank.py.

Pure computation / file-I/O tests against the real
data/aptitude_questions.json fixture — no mocking, no Redis.
"""

import pytest

from interview_ai.aptitude_models import (
    AptitudeCategory,
    AptitudeQuestion,
    AptitudeQuestionBank,
)
from interview_ai.aptitude_question_bank import AptitudeQuestionBankManager

QUESTIONS_FILE = "data/aptitude_questions.json"


@pytest.fixture
def manager() -> AptitudeQuestionBankManager:
    """Provide a fresh AptitudeQuestionBankManager instance for each test."""
    return AptitudeQuestionBankManager()


@pytest.fixture
def sample_questions() -> list[AptitudeQuestion]:
    """Provide a small, hand-built list of AptitudeQuestion for build tests."""
    return [
        AptitudeQuestion(
            question_id="AQ_TEST_001",
            category=AptitudeCategory.logical_reasoning,
            text="Sample logical reasoning question.",
            scenario_type=None,
        ),
        AptitudeQuestion(
            question_id="AQ_TEST_002",
            category=AptitudeCategory.situational_judgment,
            text="Sample situational judgment question.",
            scenario_type="deadline_pressure",
        ),
    ]


# ---------------------------------------------------------------------------
# load_from_file
# ---------------------------------------------------------------------------


def test_load_from_file_success(manager: AptitudeQuestionBankManager) -> None:
    """load_from_file must load all 9 questions from the JSON fixture."""
    bank = manager.load_from_file(QUESTIONS_FILE)
    assert isinstance(bank, AptitudeQuestionBank)
    assert len(bank.questions) == 9


def test_load_from_file_missing_raises(manager: AptitudeQuestionBankManager) -> None:
    """load_from_file must raise FileNotFoundError for a nonexistent path."""
    with pytest.raises(FileNotFoundError):
        manager.load_from_file("data/does_not_exist.json")


# ---------------------------------------------------------------------------
# build_question_bank
# ---------------------------------------------------------------------------


def test_build_question_bank_basic(
    manager: AptitudeQuestionBankManager,
    sample_questions: list[AptitudeQuestion],
) -> None:
    """build_question_bank must wrap the given questions with the given job_id."""
    bank = manager.build_question_bank(job_id="JOB_123", questions=sample_questions)
    assert bank.job_id == "JOB_123"
    assert len(bank.questions) == 2


# ---------------------------------------------------------------------------
# get_questions_by_category
# ---------------------------------------------------------------------------


def test_get_questions_by_category_all_three(
    manager: AptitudeQuestionBankManager,
) -> None:
    """get_questions_by_category must return exactly 3 questions for each
    of the 3 AptitudeCategory values, using the JSON fixture bank."""
    bank = manager.load_from_file(QUESTIONS_FILE)

    logical = manager.get_questions_by_category(bank, AptitudeCategory.logical_reasoning)
    situational = manager.get_questions_by_category(bank, AptitudeCategory.situational_judgment)
    analytical = manager.get_questions_by_category(bank, AptitudeCategory.analytical_thinking)

    assert len(logical) == 3
    assert len(situational) == 3
    assert len(analytical) == 3
    assert all(q.category == AptitudeCategory.logical_reasoning for q in logical)
    assert all(q.category == AptitudeCategory.situational_judgment for q in situational)
    assert all(q.category == AptitudeCategory.analytical_thinking for q in analytical)


# ---------------------------------------------------------------------------
# get_question_by_id
# ---------------------------------------------------------------------------


def test_get_question_by_id_found(manager: AptitudeQuestionBankManager) -> None:
    """get_question_by_id must return the matching AptitudeQuestion when present."""
    bank = manager.load_from_file(QUESTIONS_FILE)
    question = manager.get_question_by_id(bank, "AQ_LOGIC_001")
    assert question is not None
    assert question.question_id == "AQ_LOGIC_001"


def test_get_question_by_id_not_found(manager: AptitudeQuestionBankManager) -> None:
    """get_question_by_id must return None for an unknown question_id."""
    bank = manager.load_from_file(QUESTIONS_FILE)
    question = manager.get_question_by_id(bank, "AQ_DOES_NOT_EXIST")
    assert question is None


# ---------------------------------------------------------------------------
# return type
# ---------------------------------------------------------------------------


def test_returns_pydantic_model(manager: AptitudeQuestionBankManager) -> None:
    """load_from_file must return an AptitudeQuestionBank Pydantic model."""
    bank = manager.load_from_file(QUESTIONS_FILE)
    assert isinstance(bank, AptitudeQuestionBank)
    assert isinstance(bank.questions[0], AptitudeQuestion)
