"""
tests/test_day42_fixes.py

8 pytest tests covering the 5 targeted Day 42 bug fixes:
    1. report_generator.py    (backlog #7)
    2. answer_engine.py       (backlog #5)
    3. followup_engine.py     (backlog #14)
    4. hr_scoring_engine.py   (backlog #18)
    5. transcript_cleaner.py  (new finding)
"""

import pytest

from screening_ai.report_generator import generate_screening_report
from screening_ai.answer_engine import process_answer
from screening_ai.transcript_cleaner import get_processing_summary

from interview_ai.interview_models import (
    InterviewPhase,
    InterviewQuestion,
    InterviewQuestionCategory,
)
from interview_ai.followup_models import AnswerQuality, FollowUpAction, MAX_FOLLOWUP_ATTEMPTS
from interview_ai.followup_engine import build_followup_result, decide_followup_action

from interview_ai.hr_scoring_engine import hr_scoring_pipeline


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_answer(
    question_id: str = "q1",
    keywords_found: list | None = None,
    is_vague: bool = False,
    off_topic: bool = False,
) -> dict:
    """Build an answer dict matching the Day 25 answer_engine output schema."""
    return {
        "question_id": question_id,
        "original_text": "Some technical answer text.",
        "intent": "general",
        "keywords_found": keywords_found if keywords_found is not None else [],
        "experience_years": 0,
        "salary": None,
        "availability": "Unknown",
        "is_vague": is_vague,
        "off_topic": off_topic,
        "missing_answer": False,
    }


def _make_score(question_id: str = "q1", final_score: float = 70.0) -> dict:
    return {
        "question_id": question_id,
        "scores": {"relevance": final_score / 100},
        "final_score": final_score,
        "weights_used": {"relevance": 1.0},
    }


def _make_behavior(communication_strength: str = "Moderate") -> dict:
    return {
        "confidence": {"confidence_score": 0.7, "signals": {}},
        "sentiment": {"sentiment": "Neutral", "sentiment_score": 0.5},
        "behavior_flags": {"uncertainty": False, "contradiction": False},
        "communication_strength": communication_strength,
    }


def _make_question(
    follow_up_eligible: bool = True,
    question_id: str = "IQ_D42_001",
) -> InterviewQuestion:
    return InterviewQuestion(
        question_id=question_id,
        text="Tell me about a challenge you faced.",
        category=InterviewQuestionCategory.teamwork_culture_fit,
        phase=InterviewPhase.core_hr,
        follow_up_eligible=follow_up_eligible,
        order=1,
    )


# ---------------------------------------------------------------------------
# Fix 1 — report_generator.py (backlog #7)
# ---------------------------------------------------------------------------


def test_off_topic_with_keywords_not_flagged_missing() -> None:
    """off_topic=True with a non-empty keywords_found list must NOT be
    reported as missing/off-topic (keyword-match override)."""
    report = generate_screening_report(
        "cand-1",
        "job-1",
        [_make_answer(off_topic=True, keywords_found=["FMEA", "SPC"])],
        [_make_score()],
        [_make_behavior()],
    )
    assert report["summary"]["missing_data"] == []


def test_off_topic_without_keywords_still_flagged_missing() -> None:
    """off_topic=True with an EMPTY keywords_found list must still be
    flagged as missing/off-topic (regression guard — fix must not overcorrect)."""
    report = generate_screening_report(
        "cand-1",
        "job-1",
        [_make_answer(off_topic=True, keywords_found=[])],
        [_make_score()],
        [_make_behavior()],
    )
    assert len(report["summary"]["missing_data"]) == 1
    assert "off-topic" in report["summary"]["missing_data"][0]


# ---------------------------------------------------------------------------
# Fix 2 — answer_engine.py (backlog #5)
# ---------------------------------------------------------------------------


def test_single_word_answer_now_flagged_missing() -> None:
    """A single-word answer ('cat') must now return missing_answer=True —
    the behavior change introduced by aligning to word-count."""
    result = process_answer(question_id="q1", answer_text="cat")
    assert result["missing_answer"] is True


def test_three_word_answer_not_flagged_missing() -> None:
    """A 3-or-more-word answer must return missing_answer=False."""
    result = process_answer(question_id="q1", answer_text="I like cats")
    assert result["missing_answer"] is False


# ---------------------------------------------------------------------------
# Fix 3 — followup_engine.py (backlog #14)
# ---------------------------------------------------------------------------


def test_eligibility_override_agrees_across_functions() -> None:
    """decide_followup_action() and build_followup_result() must agree on
    the eligibility override: action=none, reason='follow_up_eligible=False'."""
    question = _make_question(follow_up_eligible=False)

    action = decide_followup_action(question, AnswerQuality.too_short, {})
    result = build_followup_result(question, AnswerQuality.too_short, {})

    assert action == FollowUpAction.none
    assert result.action == FollowUpAction.none
    assert result.reason == "follow_up_eligible=False"


def test_max_attempts_override_agrees_across_functions() -> None:
    """decide_followup_action() and build_followup_result() must agree on
    the max-attempts override: action=none, reason='max_attempts_reached'."""
    question = _make_question(follow_up_eligible=True)
    attempts = {question.question_id: MAX_FOLLOWUP_ATTEMPTS}

    action = decide_followup_action(question, AnswerQuality.no_answer, attempts)
    result = build_followup_result(question, AnswerQuality.no_answer, attempts)

    assert action == FollowUpAction.none
    assert result.action == FollowUpAction.none
    assert result.reason == "max_attempts_reached"


# ---------------------------------------------------------------------------
# Fix 4 — hr_scoring_engine.py (backlog #18)
# ---------------------------------------------------------------------------


def test_missing_required_key_raises_value_error() -> None:
    """An answer dict missing 'question_id' must raise a ValueError whose
    message mentions 'question_id', instead of crashing with a raw TypeError."""
    answers = [
        {
            "relevance_score": 0.8,
            "communication_score": 0.7,
            "confidence_score": 0.6,
        }
    ]
    with pytest.raises(ValueError, match="question_id"):
        hr_scoring_pipeline(answers)


# ---------------------------------------------------------------------------
# Fix 5 — transcript_cleaner.py (new finding)
# ---------------------------------------------------------------------------


def test_summary_counts_noise_and_language_mix_statuses() -> None:
    """get_processing_summary must count noise_detected and
    language_mixed_detected statuses, and all category counts must sum
    to total."""
    results = [
        {
            "question_id": "q1",
            "clean_text": "Some processed answer.",
            "confidence": 0.9,
            "status": "processed",
            "issue": None,
        },
        {
            "question_id": "q2",
            "clean_text": "",
            "confidence": 0.9,
            "status": "silence_detected",
            "issue": "silence",
        },
        {
            "question_id": "q3",
            "clean_text": "",
            "confidence": 0.4,
            "status": "poor_audio_detected",
            "issue": "poor_audio",
        },
        {
            "question_id": "q4",
            "clean_text": "",
            "confidence": 0.9,
            "status": "noise_detected",
            "issue": "noise",
        },
        {
            "question_id": "q5",
            "clean_text": "",
            "confidence": 0.9,
            "status": "noise_detected",
            "issue": "noise",
        },
        {
            "question_id": "q6",
            "clean_text": "",
            "confidence": 0.9,
            "status": "language_mixed_detected",
            "issue": "language_mix",
        },
    ]

    summary = get_processing_summary(results)

    assert summary["noise_detected"] == 2
    assert summary["language_mixed_detected"] == 1
    assert (
        summary["processed"]
        + summary["silence_detected"]
        + summary["poor_audio_detected"]
        + summary["noise_detected"]
        + summary["language_mixed_detected"]
        == summary["total"]
    )
