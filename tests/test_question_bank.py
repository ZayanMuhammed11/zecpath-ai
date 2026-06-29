"""
tests/test_question_bank.py

8 pytest tests for QuestionBankManager.
Redis is fully mocked — no live connection required.

Run:
    pytest tests/test_question_bank.py -v
"""

import json
import os
import sys
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from screening_ai.question_bank import QuestionBankManager
from screening_ai.question_models import (
    AnswerType,
    QuestionBank,
    QuestionCategory,
    RoleLevel,
    ScreeningQuestion,
)

# ── Helpers ────────────────────────────────────────────────────────────────────

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
QUESTIONS_FILE = os.path.join(PROJECT_ROOT, "data", "qe_screening_questions.json")


def make_question(
    question_id: str = "Q_TEST_001",
    category: QuestionCategory = QuestionCategory.skills,
    mandatory: bool = True,
    applicable_levels=None,
) -> ScreeningQuestion:
    """Factory helper to build a minimal valid ScreeningQuestion."""
    if applicable_levels is None:
        applicable_levels = [RoleLevel.all_levels]
    return ScreeningQuestion(
        question_id=question_id,
        question_text="Test question text?",
        category=category,
        answer_type=AnswerType.text,
        mandatory=mandatory,
        importance=3,
        applicable_levels=applicable_levels,
    )


def make_manager() -> QuestionBankManager:
    """Return a QuestionBankManager with a fresh MagicMock Redis client."""
    return QuestionBankManager(redis_client=MagicMock())


# ── Tests ──────────────────────────────────────────────────────────────────────


class TestLoadFromFile:
    """Test 1 — load_from_file reads the real dataset correctly."""

    def test_load_from_file(self):
        """
        Load the actual qe_screening_questions.json and verify:
        - Exactly 27 questions are returned.
        - Every item is a ScreeningQuestion instance.
        """
        manager = make_manager()
        questions = manager.load_from_file(QUESTIONS_FILE)

        assert len(questions) == 27, (
            f"Expected 27 questions, got {len(questions)}"
        )
        for q in questions:
            assert isinstance(q, ScreeningQuestion), (
                f"{q} is not a ScreeningQuestion instance"
            )


class TestBuildQuestionBank:
    """Test 2 — build_question_bank computes metadata correctly."""

    def test_build_question_bank(self):
        """
        Pass 3 mock questions with 2 distinct categories.
        Verify QuestionBank has correct total_questions and categories.
        """
        manager = make_manager()
        questions = [
            make_question("Q_A", QuestionCategory.skills),
            make_question("Q_B", QuestionCategory.skills),
            make_question("Q_C", QuestionCategory.experience),
        ]
        bank = manager.build_question_bank(
            job_id="JOB-TEST",
            job_title="Test Engineer",
            domain="automotive_manufacturing",
            questions=questions,
        )

        assert isinstance(bank, QuestionBank)
        assert bank.total_questions == 3
        assert bank.job_id == "JOB-TEST"
        assert set(bank.categories) == {"skills", "experience"}


class TestSaveAndLoadRedis:
    """Test 3 — save_to_redis and load_from_redis round-trip."""

    def test_save_and_load_redis(self):
        """
        Mock Redis set/get.
        Save a QuestionBank, then load it back and verify question count matches.
        """
        mock_redis = MagicMock()
        manager = QuestionBankManager(redis_client=mock_redis)

        questions = [
            make_question("Q_001", QuestionCategory.skills),
            make_question("Q_002", QuestionCategory.experience),
        ]
        bank = manager.build_question_bank(
            job_id="JOB-ROUND-TRIP",
            job_title="Round Trip Test",
            domain="pharma",
            questions=questions,
        )

        # Capture what was written to Redis
        manager.save_to_redis(bank)
        serialized = mock_redis.set.call_args[0][1]

        # Simulate Redis returning the stored value
        mock_redis.get.return_value = serialized

        loaded_bank = manager.load_from_redis("JOB-ROUND-TRIP")

        assert loaded_bank is not None
        assert loaded_bank.total_questions == 2
        assert loaded_bank.job_id == "JOB-ROUND-TRIP"


class TestGetQuestionsByCategory:
    """Test 4 — get_questions_by_category filters correctly."""

    def test_get_questions_by_category(self):
        """
        Build a bank with mixed categories.
        Filter by 'skills' and verify only skills questions are returned.
        """
        mock_redis = MagicMock()
        manager = QuestionBankManager(redis_client=mock_redis)

        questions = [
            make_question("Q_S1", QuestionCategory.skills),
            make_question("Q_S2", QuestionCategory.skills),
            make_question("Q_E1", QuestionCategory.experience),
        ]
        bank = manager.build_question_bank("JOB-CAT", "Category Test", "food_safety", questions)
        mock_redis.get.return_value = bank.model_dump_json()

        result = manager.get_questions_by_category("JOB-CAT", "skills")

        assert len(result) == 2
        assert all(q.category == QuestionCategory.skills for q in result)


class TestGetQuestionsByLevel:
    """Test 5 — get_questions_by_level applies all_levels + specific level logic."""

    def test_get_questions_by_level(self):
        """
        Build a bank with fresher-only, senior-only, and all_levels questions.
        Filter by 'senior' — should include senior + all_levels, exclude fresher-only.
        """
        mock_redis = MagicMock()
        manager = QuestionBankManager(redis_client=mock_redis)

        q_all = make_question("Q_ALL", applicable_levels=[RoleLevel.all_levels])
        q_senior = make_question("Q_SEN", applicable_levels=[RoleLevel.senior])
        q_fresher = make_question("Q_FRE", applicable_levels=[RoleLevel.fresher])

        bank = manager.build_question_bank("JOB-LVL", "Level Test", "automotive_manufacturing",
                                           [q_all, q_senior, q_fresher])
        mock_redis.get.return_value = bank.model_dump_json()

        result = manager.get_questions_by_level("JOB-LVL", "senior")

        returned_ids = {q.question_id for q in result}
        assert "Q_ALL" in returned_ids
        assert "Q_SEN" in returned_ids
        assert "Q_FRE" not in returned_ids


class TestGetMandatoryQuestions:
    """Test 6 — get_mandatory_questions returns only mandatory=True questions."""

    def test_get_mandatory_questions(self):
        """
        Build a bank with mandatory and optional questions.
        Verify only mandatory ones are returned.
        """
        mock_redis = MagicMock()
        manager = QuestionBankManager(redis_client=mock_redis)

        q_mand1 = make_question("Q_M1", mandatory=True)
        q_mand2 = make_question("Q_M2", mandatory=True)
        q_opt = make_question("Q_O1", mandatory=False)

        bank = manager.build_question_bank("JOB-MAND", "Mandatory Test", "pharma",
                                           [q_mand1, q_mand2, q_opt])
        mock_redis.get.return_value = bank.model_dump_json()

        result = manager.get_mandatory_questions("JOB-MAND")

        assert len(result) == 2
        assert all(q.mandatory for q in result)


class TestGetQuestionById:
    """Test 7 — get_question_by_id returns the correct question."""

    def test_get_question_by_id(self):
        """
        Load a bank with several questions.
        Request a specific question_id and verify the correct question is returned.
        """
        mock_redis = MagicMock()
        manager = QuestionBankManager(redis_client=mock_redis)

        target = make_question("Q_TARGET")
        other = make_question("Q_OTHER")

        bank = manager.build_question_bank("JOB-ID", "ID Test", "food_safety", [target, other])
        mock_redis.get.return_value = bank.model_dump_json()

        result = manager.get_question_by_id("JOB-ID", "Q_TARGET")

        assert result is not None
        assert result.question_id == "Q_TARGET"


class TestLoadFromRedisMissingKey:
    """Test 8 — load_from_redis returns None gracefully when key is absent."""

    def test_load_from_redis_missing_key(self):
        """
        Mock Redis returns None (key not found).
        Verify load_from_redis returns None without raising an exception.
        """
        mock_redis = MagicMock()
        mock_redis.get.return_value = None
        manager = QuestionBankManager(redis_client=mock_redis)

        result = manager.load_from_redis("JOB-NONEXISTENT")

        assert result is None
