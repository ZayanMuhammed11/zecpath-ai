"""
interview_ai/followup_engine.py

Dynamic Follow-Up Logic for the HR Interview Engine.
Part of Zecpath AI — Day 34, Sprint 4.

Receives already-computed AnswerQuality values and decides what follow-up
action to take. Does NOT inspect raw answer text — quality classification
is handled by a separate module built on a later day.
"""

from typing import Dict, Optional

from interview_ai.interview_models import (
    InterviewQuestion,
    InterviewQuestionCategory,
    InterviewState,
)
from interview_ai.followup_models import (
    AnswerQuality,
    FollowUpAction,
    FollowUpResult,
    MAX_FOLLOWUP_ATTEMPTS,
)
from utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Quality → action decision table (module-level for O(1) lookup)
# ---------------------------------------------------------------------------

_QUALITY_TO_ACTION: Dict[AnswerQuality, FollowUpAction] = {
    AnswerQuality.good: FollowUpAction.none,
    AnswerQuality.basic: FollowUpAction.request_example,
    AnswerQuality.too_short: FollowUpAction.request_elaboration,
    AnswerQuality.off_topic: FollowUpAction.request_clarification,
    AnswerQuality.no_answer: FollowUpAction.request_clarification,
}


# ---------------------------------------------------------------------------
# Follow-up text templates
#
# Two-tier lookup:
#   1. (FollowUpAction, InterviewQuestionCategory) → category-specific template
#   2. FollowUpAction alone                        → default template
#
# All templates use a single {text} placeholder for question.text.
# Keeping templates in one dict prevents branching logic from being
# spread across multiple functions.
# ---------------------------------------------------------------------------

_CATEGORY_TEMPLATES: Dict[tuple, str] = {
    # --- request_clarification ---
    (
        FollowUpAction.request_clarification,
        InterviewQuestionCategory.role_based_technical,
    ): (
        "Could you clarify your answer to: '{text}'? "
        "Specifically, which technical approach or tool were you referring to?"
    ),
    (
        FollowUpAction.request_clarification,
        InterviewQuestionCategory.role_based_non_technical,
    ): (
        "Could you clarify your answer to: '{text}'? "
        "A concrete situation or outcome would help."
    ),
    (
        FollowUpAction.request_clarification,
        InterviewQuestionCategory.teamwork_culture_fit,
    ): (
        "Could you clarify your answer to: '{text}'? "
        "What was your specific role or contribution in that situation?"
    ),
    # --- request_elaboration ---
    (
        FollowUpAction.request_elaboration,
        InterviewQuestionCategory.role_based_technical,
    ): (
        "Could you elaborate a bit more on: '{text}'? "
        "Feel free to walk through a technical step or implementation detail."
    ),
    (
        FollowUpAction.request_elaboration,
        InterviewQuestionCategory.career_goals,
    ): (
        "Could you elaborate a bit more on: '{text}'? "
        "Where do you see yourself specifically in the next few years?"
    ),
    (
        FollowUpAction.request_elaboration,
        InterviewQuestionCategory.strengths_weaknesses,
    ): (
        "Could you elaborate a bit more on: '{text}'? "
        "How has this shaped the way you work?"
    ),
    # --- request_example ---
    (
        FollowUpAction.request_example,
        InterviewQuestionCategory.role_based_technical,
    ): (
        "Could you give a specific technical example related to: '{text}'?"
    ),
    (
        FollowUpAction.request_example,
        InterviewQuestionCategory.teamwork_culture_fit,
    ): (
        "Could you give a specific example of a team situation related to: '{text}'?"
    ),
    (
        FollowUpAction.request_example,
        InterviewQuestionCategory.strengths_weaknesses,
    ): (
        "Could you give a concrete example that illustrates your answer to: '{text}'?"
    ),
    (
        FollowUpAction.request_example,
        InterviewQuestionCategory.career_goals,
    ): (
        "Could you give a specific example of a step you have taken toward: '{text}'?"
    ),
}

_DEFAULT_TEMPLATES: Dict[FollowUpAction, str] = {
    FollowUpAction.request_clarification: (
        "Could you clarify your answer to: '{text}'?"
    ),
    FollowUpAction.request_elaboration: (
        "Could you elaborate a bit more on: '{text}'?"
    ),
    FollowUpAction.request_example: (
        "Could you give a specific example related to: '{text}'?"
    ),
}


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------


def _resolve_override_reason(
    question: InterviewQuestion,
    follow_up_attempts: Dict[str, int],
) -> Optional[str]:
    """
    Single source of truth for the two follow-up overrides.

    DAY 42 FIX (backlog #14): decide_followup_action() and
    build_followup_result() previously re-checked these same two
    conditions independently. Consolidating them here means a future
    third override only needs to be added in one place.

    Args:
        question: The InterviewQuestion being evaluated.
        follow_up_attempts: Mapping of question_id → follow-up count used so far.

    Returns:
        "follow_up_eligible=False" if question.follow_up_eligible is False,
        "max_attempts_reached" if the attempt count for this question has
        reached MAX_FOLLOWUP_ATTEMPTS, or None if neither override applies.
    """
    if not question.follow_up_eligible:
        return "follow_up_eligible=False"
    if follow_up_attempts.get(question.question_id, 0) >= MAX_FOLLOWUP_ATTEMPTS:
        return "max_attempts_reached"
    return None


def decide_followup_action(
    question: InterviewQuestion,
    quality: AnswerQuality,
    follow_up_attempts: Dict[str, int],
) -> FollowUpAction:
    """
    Determine the follow-up action for a question based on answer quality.

    Override checks are applied BEFORE the quality-based decision table.
    Either override forces FollowUpAction.none:
      1. question.follow_up_eligible is False
      2. follow_up_attempts[question_id] >= MAX_FOLLOWUP_ATTEMPTS

    Decision table (applied only when both overrides pass):
      AnswerQuality.good        → FollowUpAction.none
      AnswerQuality.basic       → FollowUpAction.request_example
      AnswerQuality.too_short   → FollowUpAction.request_elaboration
      AnswerQuality.off_topic   → FollowUpAction.request_clarification
      AnswerQuality.no_answer   → FollowUpAction.request_clarification

    This is a pure function — same inputs always produce the same output.
    No randomness; no side effects.

    Args:
        question: The InterviewQuestion being evaluated.
        quality: Already-computed AnswerQuality classification from the caller.
        follow_up_attempts: Mapping of question_id → follow-up count used so far.

    Returns:
        The FollowUpAction the conversation engine should take.
    """
    qid = question.question_id
    override_reason = _resolve_override_reason(question, follow_up_attempts)

    if override_reason is not None:
        logger.info(
            "decide_followup_action | question_id=%s quality=%s action=%s "
            "(override: %s)",
            qid,
            quality.value,
            FollowUpAction.none.value,
            override_reason,
        )
        return FollowUpAction.none

    action = _QUALITY_TO_ACTION[quality]
    logger.info(
        "decide_followup_action | question_id=%s quality=%s action=%s",
        qid,
        quality.value,
        action.value,
    )
    return action


def generate_followup_text(
    question: InterviewQuestion,
    action: FollowUpAction,
) -> Optional[str]:
    """
    Produce a deterministic follow-up prompt string for the given action.

    Returns None when action is FollowUpAction.none. Otherwise performs a
    two-tier template lookup: category-specific first (_CATEGORY_TEMPLATES),
    then action-level default (_DEFAULT_TEMPLATES). All templates reference
    question.text via the '{text}' placeholder.

    No randomness; same inputs always produce the same output.

    Args:
        question: The InterviewQuestion being followed up on.
        action: The FollowUpAction chosen by decide_followup_action().

    Returns:
        A formatted follow-up prompt string, or None when action is 'none'.
    """
    if action is FollowUpAction.none:
        return None

    template = _CATEGORY_TEMPLATES.get(
        (action, question.category),
        _DEFAULT_TEMPLATES[action],
    )
    return template.format(text=question.text)


def build_followup_result(
    question: InterviewQuestion,
    quality: AnswerQuality,
    follow_up_attempts: Dict[str, int],
) -> FollowUpResult:
    """
    Orchestrate a complete follow-up decision and return a FollowUpResult.

    Calls decide_followup_action() to determine the action, then
    generate_followup_text() to produce the prompt text. Assembles a
    FollowUpResult with a reason string that identifies which branch fired:
      - "follow_up_eligible=False"  — eligibility override
      - "max_attempts_reached"      — attempt-limit override
      - "quality=<value>"           — quality-table-driven decision

    The reason-string branching mirrors the override order in
    decide_followup_action() so the two stay in sync.

    Args:
        question: The InterviewQuestion being evaluated.
        quality: Already-computed AnswerQuality classification from the caller.
        follow_up_attempts: Mapping of question_id → follow-up count used so far.

    Returns:
        A fully populated FollowUpResult instance.
    """
    qid = question.question_id
    action = decide_followup_action(question, quality, follow_up_attempts)
    follow_up_text = generate_followup_text(question, action)

    # DAY 42 FIX (backlog #14): reason string now derived from the same
    # _resolve_override_reason() helper decide_followup_action() uses,
    # instead of an independently re-checked copy of the same conditions.
    override_reason = _resolve_override_reason(question, follow_up_attempts)
    reason = override_reason if override_reason is not None else f"quality={quality.value}"

    result = FollowUpResult(
        question_id=qid,
        action=action,
        follow_up_text=follow_up_text,
        reason=reason,
    )

    logger.info(
        "build_followup_result | question_id=%s quality=%s action=%s reason=%s",
        qid,
        quality.value,
        action.value,
        reason,
    )
    return result


def is_repeated_question(
    state: InterviewState,
    question_id: str,
) -> bool:
    """
    Check whether a question has already been asked in this interview session.

    Read-only check — does not modify state.questions_asked.

    Args:
        state: The live InterviewState for this interview session.
        question_id: The question_id to look up.

    Returns:
        True if question_id is already in state.questions_asked, else False.
    """
    return question_id in state.questions_asked


def record_question_asked(
    state: InterviewState,
    question_id: str,
) -> InterviewState:
    """
    Return a new InterviewState with question_id appended to questions_asked.

    Idempotent: if question_id is already present the returned state carries
    the same questions_asked list with no duplicate added.

    Never mutates the input state — uses Pydantic's model_copy(update=...) in
    both branches to guarantee the caller's original object is unchanged.

    Args:
        state: The current InterviewState.
        question_id: The question_id to record as asked.

    Returns:
        A new InterviewState instance with the updated questions_asked list.
    """
    if question_id in state.questions_asked:
        # Already recorded — return an identical copy without duplicating
        return state.model_copy()

    updated = list(state.questions_asked) + [question_id]
    return state.model_copy(update={"questions_asked": updated})
