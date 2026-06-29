"""
interview_ai/followup_models.py

Pydantic v2 models and enums for the Dynamic Follow-Up Logic layer.
Part of Zecpath AI — Day 34, Sprint 4.

CRITICAL: AnswerQuality represents an already-computed classification
supplied by the caller. This module does NOT compute or classify answer
quality from raw text — that work is performed by a separate module
built on a later day.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class AnswerQuality(str, Enum):
    """
    Quality classification of a candidate's answer to an interview question.

    IMPORTANT: This enum represents an already-computed classification
    supplied by the caller. This module does not compute it — quality
    classification from raw answer text is handled by a separate module
    built on a later day. No function in followup_engine.py inspects
    raw answer strings.
    """

    good = "good"
    basic = "basic"
    too_short = "too_short"
    off_topic = "off_topic"
    no_answer = "no_answer"


class FollowUpAction(str, Enum):
    """Action the conversation engine should take after evaluating answer quality."""

    none = "none"
    request_clarification = "request_clarification"
    request_elaboration = "request_elaboration"
    request_example = "request_example"


# Matches MAX_RETRIES=2 convention in screening_ai/conversation_flow.py (Day 29)
MAX_FOLLOWUP_ATTEMPTS: int = 2


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class FollowUpResult(BaseModel):
    """
    Encapsulates the outcome of a follow-up decision for a single question.

    Produced by followup_engine.build_followup_result() and consumed by
    the conversation engine to determine whether and how to re-prompt
    the candidate.
    """

    question_id: str = Field(
        ...,
        description="The question_id this result applies to",
    )
    action: FollowUpAction = Field(
        ...,
        description="The follow-up action the engine should take",
    )
    follow_up_text: Optional[str] = Field(
        default=None,
        description=(
            "Templated follow-up prompt text presented to the candidate; "
            "None when action is 'none'"
        ),
    )
    reason: str = Field(
        ...,
        description=(
            "Short human-readable explanation of why this action was chosen, "
            "e.g. 'quality=too_short', 'follow_up_eligible=False', "
            "'max_attempts_reached'"
        ),
    )
