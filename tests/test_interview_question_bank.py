"""
tests/test_interview_question_bank.py

8 pytest tests for InterviewQuestionBankManager.
Redis is fully mocked — no live connection required.

Mocking approach: unittest.mock.MagicMock, matching tests/test_question_bank.py
exactly. redis_client is a MagicMock passed directly to the methods that need
it (save_to_redis, load_from_redis) because InterviewQuestionBankManager is
stateless — no redis_client stored in __init__.

Run:
    pytest tests/test_interview_question_bank.py -v
"""

import os
import sys
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from interview_ai.interview_models import (
    InterviewPhase,
    InterviewQuestion,
    InterviewQuestionBank,
    InterviewQuestionCategory,
    RoleLevel,
    RoleType,
    resolve_role_level,
)
from interview_ai.interview_question_bank import InterviewQuestionBankManager

# ── Helpers ────────────────────────────────────────────────────────────────────

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
QUESTIONS_FILE = os.path.join(PROJECT_ROOT, "data", "hr_interview_questions.json")


def make_question(
    question_id: str = "IQ_TEST_001",
    category: InterviewQuestionCategory = InterviewQuestionCategory.teamwork_culture_fit,
    phase: InterviewPhase = InterviewPhase.core_hr,
    applicable_levels: list | None = None,
    applicable_role_types: list | None = None,
    order: int = 1,
) -> InterviewQuestion:
    """Factory helper to build a minimal valid InterviewQuestion."""
    if applicable_levels is None:
        applicable_levels = [RoleLevel.all_levels]
    if applicable_role_types is None:
        applicable_role_types = [RoleType.technical, RoleType.non_technical]
    return InterviewQuestion(
        question_id=question_id,
        text="Test interview question?",
        category=category,
        phase=phase,
        applicable_levels=applicable_levels,
        applicable_role_types=applicable_role_types,
        order=order,
    )


def make_manager() -> InterviewQuestionBankManager:
    """
    Return a fresh InterviewQuestionBankManager.

    No constructor arguments — redis_client is passed per-method call.
    """
    return InterviewQuestionBankManager()


# ── Tests ──────────────────────────────────────────────────────────────────────


class TestLoadFromFile:
    """Test 1 — load_from_file reads the real dataset correctly."""

    def test_load_from_file_parses_correctly(self):
        """
        Load the actual hr_interview_questions.json and verify:
        - Exactly 20 questions are returned.
        - Every item is an InterviewQuestion instance.
        """
        manager = make_manager()
        questions = manager.load_from_file(QUESTIONS_FILE)

        assert len(questions) == 20, (
            f"Expected 20 questions, got {len(questions)}"
        )
        for q in questions:
            assert isinstance(q, InterviewQuestion), (
                f"{q!r} is not an InterviewQuestion instance"
            )


class TestBuildQuestionBank:
    """Test 2 — build_question_bank computes total_questions correctly."""

    def test_build_question_bank_total_questions_correct(self):
        """
        Pass 4 mock questions.
        Verify InterviewQuestionBank has correct total_questions and job_id.
        """
        manager = make_manager()
        questions = [
            make_question("IQ_A", order=1),
            make_question("IQ_B", order=2),
            make_question("IQ_C", order=3),
            make_question("IQ_D", order=4),
        ]
        bank = manager.build_question_bank(job_id="JOB-TEST", questions=questions)

        assert isinstance(bank, InterviewQuestionBank)
        assert bank.total_questions == 4
        assert bank.job_id == "JOB-TEST"
        assert len(bank.questions) == 4


class TestSaveAndLoadRedis:
    """Test 3 — save_to_redis and load_from_redis round-trip."""

    def test_save_and_load_redis_round_trip(self):
        """
        Mock Redis set/get.
        Save an InterviewQuestionBank, then load it back and verify equality.
        """
        mock_redis = MagicMock()
        manager = make_manager()

        questions = [
            make_question("IQ_RT_001", order=1),
            make_question("IQ_RT_002", order=2),
            make_question("IQ_RT_003", order=3),
        ]
        bank = manager.build_question_bank(
            job_id="JOB-ROUND-TRIP", questions=questions
        )

        # Capture what was written to Redis
        manager.save_to_redis(bank, mock_redis)
        serialized = mock_redis.set.call_args[0][1]

        # Simulate Redis returning the stored value on the next get
        mock_redis.get.return_value = serialized

        loaded_bank = manager.load_from_redis("JOB-ROUND-TRIP", mock_redis)

        assert loaded_bank is not None
        assert loaded_bank.total_questions == 3
        assert loaded_bank.job_id == "JOB-ROUND-TRIP"
        assert loaded_bank == bank


class TestGetQuestionsByPhase:
    """Test 4 — get_questions_by_phase filters and sorts correctly."""

    def test_get_questions_by_phase_filters_correctly(self):
        """
        Build a bank with questions spread across multiple phases.
        Filter by core_hr and verify:
        - Only core_hr questions are returned.
        - Results are sorted ascending by order.
        """
        manager = make_manager()
        questions = [
            make_question("IQ_PH_INTRO", phase=InterviewPhase.introduction, order=1),
            make_question("IQ_PH_HR_A",  phase=InterviewPhase.core_hr,      order=2),
            make_question("IQ_PH_HR_B",  phase=InterviewPhase.core_hr,      order=1),
            make_question("IQ_PH_CLOSE", phase=InterviewPhase.closing,       order=1),
        ]
        bank = manager.build_question_bank(job_id="JOB-PHASE", questions=questions)

        result = manager.get_questions_by_phase(bank, InterviewPhase.core_hr)

        assert len(result) == 2
        assert all(q.phase == InterviewPhase.core_hr for q in result)
        # Verify sorted ascending by order — lower order comes first
        assert result[0].order < result[1].order
        assert result[0].question_id == "IQ_PH_HR_B"
        assert result[1].question_id == "IQ_PH_HR_A"


class TestGenerateFresherTechnical:
    """Test 5 — generate_interview_questions for fresher + technical."""

    def test_generate_interview_questions_fresher_technical(self):
        """
        Build a mixed bank. Generate for RoleLevel.fresher + RoleType.technical.
        Assert:
        - Includes: all_levels + both, all_levels + technical, fresher + technical
        - Excludes: non_technical-only, senior-only, mid-only
        """
        manager = make_manager()
        questions = [
            make_question(
                "IQ_ALL_BOTH",
                applicable_levels=[RoleLevel.all_levels],
                applicable_role_types=[RoleType.technical, RoleType.non_technical],
                order=1,
            ),
            make_question(
                "IQ_ALL_TECH",
                applicable_levels=[RoleLevel.all_levels],
                applicable_role_types=[RoleType.technical],
                order=2,
            ),
            make_question(
                "IQ_ALL_NONTECH",
                applicable_levels=[RoleLevel.all_levels],
                applicable_role_types=[RoleType.non_technical],
                order=3,
            ),
            make_question(
                "IQ_FRESH_TECH",
                applicable_levels=[RoleLevel.fresher],
                applicable_role_types=[RoleType.technical],
                order=4,
            ),
            make_question(
                "IQ_SENIOR_NONTECH",
                applicable_levels=[RoleLevel.senior],
                applicable_role_types=[RoleType.non_technical],
                order=5,
            ),
            make_question(
                "IQ_MID_BOTH",
                applicable_levels=[RoleLevel.mid],
                applicable_role_types=[RoleType.technical, RoleType.non_technical],
                order=6,
            ),
        ]
        bank = manager.build_question_bank(
            job_id="JOB-FRESH-TECH", questions=questions
        )

        result = manager.generate_interview_questions(
            bank, RoleLevel.fresher, RoleType.technical
        )
        result_ids = {q.question_id for q in result}

        assert "IQ_ALL_BOTH"       in result_ids
        assert "IQ_ALL_TECH"       in result_ids
        assert "IQ_FRESH_TECH"     in result_ids
        assert "IQ_ALL_NONTECH"    not in result_ids
        assert "IQ_SENIOR_NONTECH" not in result_ids
        assert "IQ_MID_BOTH"       not in result_ids


class TestGenerateSeniorNonTechnical:
    """Test 6 — generate_interview_questions for senior + non_technical."""

    def test_generate_interview_questions_senior_non_technical(self):
        """
        Build a mixed bank. Generate for RoleLevel.senior + RoleType.non_technical.
        Assert:
        - Includes: all_levels + both, all_levels + non_technical, senior + non_technical
        - Excludes: technical-only, fresher-only, mid-only
        """
        manager = make_manager()
        questions = [
            make_question(
                "IQ_ALL_BOTH",
                applicable_levels=[RoleLevel.all_levels],
                applicable_role_types=[RoleType.technical, RoleType.non_technical],
                order=1,
            ),
            make_question(
                "IQ_ALL_TECH",
                applicable_levels=[RoleLevel.all_levels],
                applicable_role_types=[RoleType.technical],
                order=2,
            ),
            make_question(
                "IQ_ALL_NONTECH",
                applicable_levels=[RoleLevel.all_levels],
                applicable_role_types=[RoleType.non_technical],
                order=3,
            ),
            make_question(
                "IQ_FRESH_TECH",
                applicable_levels=[RoleLevel.fresher],
                applicable_role_types=[RoleType.technical],
                order=4,
            ),
            make_question(
                "IQ_SENIOR_NONTECH",
                applicable_levels=[RoleLevel.senior],
                applicable_role_types=[RoleType.non_technical],
                order=5,
            ),
            make_question(
                "IQ_MID_BOTH",
                applicable_levels=[RoleLevel.mid],
                applicable_role_types=[RoleType.technical, RoleType.non_technical],
                order=6,
            ),
        ]
        bank = manager.build_question_bank(
            job_id="JOB-SENIOR-NT", questions=questions
        )

        result = manager.generate_interview_questions(
            bank, RoleLevel.senior, RoleType.non_technical
        )
        result_ids = {q.question_id for q in result}

        assert "IQ_ALL_BOTH"       in result_ids
        assert "IQ_ALL_NONTECH"    in result_ids
        assert "IQ_SENIOR_NONTECH" in result_ids
        assert "IQ_ALL_TECH"       not in result_ids
        assert "IQ_FRESH_TECH"     not in result_ids
        assert "IQ_MID_BOTH"       not in result_ids


class TestDeterminism:
    """Test 7 — generate_interview_questions is deterministic."""

    def test_generate_interview_questions_is_deterministic(self):
        """
        Call generate_interview_questions twice with identical arguments.
        Assert both calls return lists equal element-for-element in the
        same order — no randomness, no sort instability.

        Questions are intentionally provided out of natural order so
        sorting is observable, not coincidental.
        """
        manager_a = make_manager()
        manager_b = make_manager()

        questions = [
            make_question("IQ_DET_001", phase=InterviewPhase.introduction, order=3),
            make_question("IQ_DET_002", phase=InterviewPhase.core_hr,      order=2),
            make_question("IQ_DET_003", phase=InterviewPhase.introduction, order=1),
            make_question("IQ_DET_004", phase=InterviewPhase.closing,      order=1),
            make_question("IQ_DET_005", phase=InterviewPhase.core_hr,      order=1),
        ]
        bank = manager_a.build_question_bank(job_id="JOB-DET", questions=questions)

        result_1 = manager_a.generate_interview_questions(
            bank, RoleLevel.mid, RoleType.technical
        )
        result_2 = manager_b.generate_interview_questions(
            bank, RoleLevel.mid, RoleType.technical
        )

        assert len(result_1) == len(result_2), (
            "Determinism failure: call counts differ"
        )
        for idx, (q1, q2) in enumerate(zip(result_1, result_2)):
            assert q1.question_id == q2.question_id, (
                f"Determinism failure at position {idx}: "
                f"{q1.question_id!r} != {q2.question_id!r}"
            )

        # Verify the sort contract explicitly
        ids = [q.question_id for q in result_1]
        assert ids.index("IQ_DET_003") < ids.index("IQ_DET_001"), (
            "introduction order=1 must precede introduction order=3"
        )
        assert ids.index("IQ_DET_001") < ids.index("IQ_DET_005"), (
            "introduction phase must precede core_hr phase"
        )
        assert ids.index("IQ_DET_005") < ids.index("IQ_DET_002"), (
            "core_hr order=1 must precede core_hr order=2"
        )
        assert ids.index("IQ_DET_002") < ids.index("IQ_DET_004"), (
            "core_hr phase must precede closing phase"
        )


class TestResolveRoleLevel:
    """Test 8 — resolve_role_level boundary conditions."""

    def test_resolve_role_level_boundaries(self):
        """
        Verify the four boundary values match scoring/ats_scorer.py bands.

          11 months → fresher   (< FRESHER_MAX_MONTHS=12)
          12 months → mid       (>= 12, < MID_MAX_MONTHS=84)
          83 months → mid       (>= 12, < 84)
          84 months → senior    (>= MID_MAX_MONTHS=84)
        """
        assert resolve_role_level(11) == RoleLevel.fresher, (
            "11 months should resolve to fresher (boundary: < 12)"
        )
        assert resolve_role_level(12) == RoleLevel.mid, (
            "12 months should resolve to mid (boundary: >= 12)"
        )
        assert resolve_role_level(83) == RoleLevel.mid, (
            "83 months should resolve to mid (boundary: < 84)"
        )
        assert resolve_role_level(84) == RoleLevel.senior, (
            "84 months should resolve to senior (boundary: >= 84)"
        )
