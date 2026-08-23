"""
tests/test_technical_question_bank.py

Unit tests for technical_ai.technical_question_bank.TechnicalQuestionBankManager.

File I/O is mocked via pytest's tmp_path fixture — tests do not depend on
the real data file at data/technical_interview_questions.json so they
keep passing even if that content changes later.
"""

import json

import pytest

from technical_ai.technical_interview_models import (
    TechnicalDifficulty,
    TechnicalInterviewPhase,
    TechnicalInterviewQuestion,
    TechnicalInterviewQuestionBank,
    TechnicalSkillDomain,
)
from technical_ai.technical_question_bank import TechnicalQuestionBankManager


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _valid_question_dicts():
    return [
        {
            "question_id": "TQ_AUTO_INTRO_001",
            "text": "Tell me about your automotive quality background.",
            "skill_domain": "automotive_quality",
            "phase": "introduction",
            "applicable_difficulties": ["basic"],
            "order": 1,
        },
        {
            "question_id": "TQ_AUTO_EXP_001",
            "text": "Walk me through a Control Plan you built.",
            "skill_domain": "automotive_quality",
            "phase": "experience_based",
            "applicable_difficulties": ["intermediate", "advanced"],
            "order": 1,
        },
        {
            "question_id": "TQ_AUTO_CONC_001",
            "text": "Explain SPC control charts.",
            "skill_domain": "automotive_quality",
            "phase": "conceptual",
            "applicable_difficulties": ["intermediate", "advanced"],
            "order": 1,
        },
    ]


@pytest.fixture
def manager() -> TechnicalQuestionBankManager:
    return TechnicalQuestionBankManager()


@pytest.fixture
def valid_questions_file(tmp_path):
    filepath = tmp_path / "questions.json"
    filepath.write_text(json.dumps(_valid_question_dicts()), encoding="utf-8")
    return str(filepath)


# ---------------------------------------------------------------------------
# load_from_file
# ---------------------------------------------------------------------------


def test_load_from_file_success(manager, valid_questions_file):
    questions = manager.load_from_file(valid_questions_file)
    assert len(questions) == 3
    assert all(isinstance(q, TechnicalInterviewQuestion) for q in questions)


def test_load_from_file_missing_file_raises(manager, tmp_path):
    missing_path = str(tmp_path / "does_not_exist.json")
    with pytest.raises(FileNotFoundError):
        manager.load_from_file(missing_path)


def test_load_from_file_invalid_entry_raises_value_error(manager, tmp_path):
    bad_data = _valid_question_dicts()
    # Invalid: empty applicable_difficulties
    bad_data.append(
        {
            "question_id": "TQ_AUTO_CLOSE_999",
            "text": "Bad question.",
            "skill_domain": "automotive_quality",
            "phase": "closing",
            "applicable_difficulties": [],
            "order": 1,
        }
    )
    filepath = tmp_path / "bad_questions.json"
    filepath.write_text(json.dumps(bad_data), encoding="utf-8")

    with pytest.raises(ValueError):
        manager.load_from_file(str(filepath))


# ---------------------------------------------------------------------------
# build_question_bank
# ---------------------------------------------------------------------------


def test_build_question_bank_success(manager, valid_questions_file):
    questions = manager.load_from_file(valid_questions_file)
    bank = manager.build_question_bank(
        job_id="JOB123",
        skill_domain=TechnicalSkillDomain.automotive_quality,
        questions=questions,
    )
    assert isinstance(bank, TechnicalInterviewQuestionBank)
    assert bank.total_questions == 3
    assert bank.skill_domain == TechnicalSkillDomain.automotive_quality


def test_build_question_bank_domain_mismatch_raises(manager, valid_questions_file):
    questions = manager.load_from_file(valid_questions_file)
    with pytest.raises(ValueError) as exc_info:
        manager.build_question_bank(
            job_id="JOB123",
            skill_domain=TechnicalSkillDomain.food_safety_systems,
            questions=questions,
        )
    # All three automotive questions should be listed as mismatched
    for question in questions:
        assert question.question_id in str(exc_info.value)


# ---------------------------------------------------------------------------
# get_questions_by_phase
# ---------------------------------------------------------------------------


def test_get_questions_by_phase_filters_and_sorts(manager):
    q1 = TechnicalInterviewQuestion(
        question_id="TQ_AUTO_CONC_002",
        text="Second conceptual question.",
        skill_domain=TechnicalSkillDomain.automotive_quality,
        phase=TechnicalInterviewPhase.conceptual,
        applicable_difficulties=[TechnicalDifficulty.advanced],
        order=2,
    )
    q2 = TechnicalInterviewQuestion(
        question_id="TQ_AUTO_CONC_001",
        text="First conceptual question.",
        skill_domain=TechnicalSkillDomain.automotive_quality,
        phase=TechnicalInterviewPhase.conceptual,
        applicable_difficulties=[TechnicalDifficulty.basic],
        order=1,
    )
    q3 = TechnicalInterviewQuestion(
        question_id="TQ_AUTO_INTRO_001",
        text="Intro question.",
        skill_domain=TechnicalSkillDomain.automotive_quality,
        phase=TechnicalInterviewPhase.introduction,
        applicable_difficulties=[TechnicalDifficulty.basic],
        order=1,
    )
    bank = TechnicalInterviewQuestionBank(
        job_id="JOB123",
        skill_domain=TechnicalSkillDomain.automotive_quality,
        questions=[q1, q2, q3],
        total_questions=3,
    )

    result = manager.get_questions_by_phase(
        bank, TechnicalInterviewPhase.conceptual
    )
    assert [q.question_id for q in result] == [
        "TQ_AUTO_CONC_001",
        "TQ_AUTO_CONC_002",
    ]


def test_get_questions_by_phase_empty_result(manager):
    bank = TechnicalInterviewQuestionBank(
        job_id="JOB123",
        skill_domain=TechnicalSkillDomain.automotive_quality,
        questions=[],
        total_questions=0,
    )
    result = manager.get_questions_by_phase(
        bank, TechnicalInterviewPhase.closing
    )
    assert result == []


# ---------------------------------------------------------------------------
# generate_interview_questions
# ---------------------------------------------------------------------------


def test_generate_interview_questions_filters_by_difficulty_and_sorts_deterministically(
    manager,
):
    q_closing = TechnicalInterviewQuestion(
        question_id="TQ_AUTO_CLOSE_001",
        text="Closing question.",
        skill_domain=TechnicalSkillDomain.automotive_quality,
        phase=TechnicalInterviewPhase.closing,
        applicable_difficulties=[TechnicalDifficulty.intermediate],
        order=1,
    )
    q_intro = TechnicalInterviewQuestion(
        question_id="TQ_AUTO_INTRO_001",
        text="Intro question.",
        skill_domain=TechnicalSkillDomain.automotive_quality,
        phase=TechnicalInterviewPhase.introduction,
        applicable_difficulties=[TechnicalDifficulty.intermediate],
        order=1,
    )
    q_advanced_only = TechnicalInterviewQuestion(
        question_id="TQ_AUTO_SCEN_001",
        text="Advanced scenario question.",
        skill_domain=TechnicalSkillDomain.automotive_quality,
        phase=TechnicalInterviewPhase.scenario_based,
        applicable_difficulties=[TechnicalDifficulty.advanced],
        order=1,
    )
    bank = TechnicalInterviewQuestionBank(
        job_id="JOB123",
        skill_domain=TechnicalSkillDomain.automotive_quality,
        questions=[q_closing, q_intro, q_advanced_only],
        total_questions=3,
    )

    result = manager.generate_interview_questions(
        bank, TechnicalDifficulty.intermediate
    )
    # advanced-only question should be excluded; intro (phase 0) before
    # closing (phase 4)
    assert [q.question_id for q in result] == [
        "TQ_AUTO_INTRO_001",
        "TQ_AUTO_CLOSE_001",
    ]


def test_generate_interview_questions_is_deterministic_across_calls(manager):
    questions = [
        TechnicalInterviewQuestion(
            question_id=f"TQ_AUTO_CONC_{i:03d}",
            text=f"Question {i}",
            skill_domain=TechnicalSkillDomain.automotive_quality,
            phase=TechnicalInterviewPhase.conceptual,
            applicable_difficulties=[TechnicalDifficulty.basic],
            order=i,
        )
        for i in range(5, 0, -1)
    ]
    bank = TechnicalInterviewQuestionBank(
        job_id="JOB123",
        skill_domain=TechnicalSkillDomain.automotive_quality,
        questions=questions,
        total_questions=len(questions),
    )

    first_call = manager.generate_interview_questions(bank, TechnicalDifficulty.basic)
    second_call = manager.generate_interview_questions(bank, TechnicalDifficulty.basic)

    assert [q.question_id for q in first_call] == [
        q.question_id for q in second_call
    ]
    assert [q.order for q in first_call] == [1, 2, 3, 4, 5]


def test_generate_interview_questions_empty_bank(manager):
    bank = TechnicalInterviewQuestionBank(
        job_id="JOB123",
        skill_domain=TechnicalSkillDomain.automotive_quality,
        questions=[],
        total_questions=0,
    )
    result = manager.generate_interview_questions(bank, TechnicalDifficulty.advanced)
    assert result == []
