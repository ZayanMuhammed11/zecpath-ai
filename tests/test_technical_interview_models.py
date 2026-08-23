"""
tests/test_technical_interview_models.py

Unit tests for technical_ai.technical_interview_models.
"""

import pytest
from pydantic import ValidationError

from technical_ai.technical_interview_models import (
    TechnicalDifficulty,
    TechnicalInterviewPhase,
    TechnicalInterviewQuestion,
    TechnicalInterviewQuestionBank,
    TechnicalInterviewState,
    TechnicalSkillDomain,
    resolve_technical_difficulty,
)


# ---------------------------------------------------------------------------
# resolve_technical_difficulty boundary tests
# ---------------------------------------------------------------------------


def test_resolve_technical_difficulty_below_basic_boundary():
    assert resolve_technical_difficulty(23) == TechnicalDifficulty.basic


def test_resolve_technical_difficulty_at_basic_boundary():
    # 24 months is the start of the intermediate band per the brief
    assert resolve_technical_difficulty(24) == TechnicalDifficulty.intermediate


def test_resolve_technical_difficulty_just_above_basic_boundary():
    assert resolve_technical_difficulty(25) == TechnicalDifficulty.intermediate


def test_resolve_technical_difficulty_below_intermediate_boundary():
    assert resolve_technical_difficulty(59) == TechnicalDifficulty.intermediate


def test_resolve_technical_difficulty_at_intermediate_boundary():
    # 60 months (5 years) is still intermediate per the brief
    assert resolve_technical_difficulty(60) == TechnicalDifficulty.intermediate


def test_resolve_technical_difficulty_just_above_intermediate_boundary():
    assert resolve_technical_difficulty(61) == TechnicalDifficulty.advanced


def test_resolve_technical_difficulty_zero_months():
    assert resolve_technical_difficulty(0) == TechnicalDifficulty.basic


# ---------------------------------------------------------------------------
# TechnicalInterviewQuestion validator
# ---------------------------------------------------------------------------


def test_technical_interview_question_rejects_empty_applicable_difficulties():
    with pytest.raises(ValidationError):
        TechnicalInterviewQuestion(
            question_id="TQ_AUTO_INTRO_999",
            text="Placeholder question text.",
            skill_domain=TechnicalSkillDomain.automotive_quality,
            phase=TechnicalInterviewPhase.introduction,
            applicable_difficulties=[],
            order=1,
        )


def test_technical_interview_question_accepts_valid_difficulties():
    question = TechnicalInterviewQuestion(
        question_id="TQ_AUTO_INTRO_999",
        text="Placeholder question text.",
        skill_domain=TechnicalSkillDomain.automotive_quality,
        phase=TechnicalInterviewPhase.introduction,
        applicable_difficulties=[TechnicalDifficulty.basic],
        order=1,
    )
    assert question.applicable_difficulties == [TechnicalDifficulty.basic]


# ---------------------------------------------------------------------------
# isinstance / model shape checks
# ---------------------------------------------------------------------------


def test_technical_interview_question_is_instance():
    question = TechnicalInterviewQuestion(
        question_id="TQ_FOOD_CONC_999",
        text="Placeholder conceptual question.",
        skill_domain=TechnicalSkillDomain.food_safety_systems,
        phase=TechnicalInterviewPhase.conceptual,
        applicable_difficulties=[TechnicalDifficulty.intermediate],
        order=2,
    )
    assert isinstance(question, TechnicalInterviewQuestion)
    assert question.follow_up_eligible is True


def test_technical_interview_question_bank_is_instance():
    question = TechnicalInterviewQuestion(
        question_id="TQ_PHARMA_SCEN_999",
        text="Placeholder scenario question.",
        skill_domain=TechnicalSkillDomain.pharmaceutical_quality,
        phase=TechnicalInterviewPhase.scenario_based,
        applicable_difficulties=[TechnicalDifficulty.advanced],
        order=1,
    )
    bank = TechnicalInterviewQuestionBank(
        job_id="JOB123",
        skill_domain=TechnicalSkillDomain.pharmaceutical_quality,
        questions=[question],
        total_questions=1,
    )
    assert isinstance(bank, TechnicalInterviewQuestionBank)
    assert bank.version == "1.0.0"
    assert bank.total_questions == 1


def test_technical_interview_state_is_instance():
    state = TechnicalInterviewState(
        candidate_id="CAND001",
        job_id="JOB123",
        skill_domain=TechnicalSkillDomain.automotive_quality,
        current_phase=TechnicalInterviewPhase.introduction,
        current_difficulty=TechnicalDifficulty.basic,
    )
    assert isinstance(state, TechnicalInterviewState)
    assert state.completed is False
    assert state.questions_asked == []
    assert state.current_question_id is None


def test_technical_interview_phase_declaration_order():
    phases = list(TechnicalInterviewPhase)
    assert phases == [
        TechnicalInterviewPhase.introduction,
        TechnicalInterviewPhase.experience_based,
        TechnicalInterviewPhase.conceptual,
        TechnicalInterviewPhase.scenario_based,
        TechnicalInterviewPhase.closing,
    ]
