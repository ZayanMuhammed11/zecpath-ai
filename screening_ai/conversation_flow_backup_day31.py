"""Conversation state machine for AI screening interview flow.

This module drives a single screening interview through its question
list: it tracks which question is currently in focus, classifies each
candidate response (silence, poor audio, too short, or valid),
decides whether to retry, skip, or accept and advance, and records
clean question/answer exchanges to an in-memory history.

Day 29 of the Zecpath AI screening pipeline build.
"""

from utils.logger import get_logger

logger = get_logger(__name__)

# Day 24's stt_processor emits exactly these three status strings.
# Keeping this set aligned with that exact contract means any drift
# in what stt_processor returns (a typo, a renamed status, a new
# value) surfaces immediately as a ValueError in record_exchange()
# instead of silently corrupting the interview history.
VALID_STT_STATUSES = {"processed", "silence_detected", "poor_audio_detected"}

# Maximum number of retry attempts allowed on a single question
# before the state machine gives up and skips ahead.
MAX_RETRIES = 2


class ConversationStateMachine:
    """Drives a single screening interview through its question list.

    The state machine owns flow logic only — it has no Redis imports
    and no knowledge of how the question bank is stored. The caller
    is responsible for loading the question list (e.g. from the
    Day 22 `question_bank:{job_id}` Redis key, accessed via .get()
    rather than dot notation) and passing it in as a plain list of
    dicts at construction time.
    """

    def __init__(self, questions: list[dict]) -> None:
        """Initialize the state machine with a pre-loaded question list.

        Args:
            questions: List of question dicts matching the Day 22
                question bank schema, each exposing "question_id",
                "question", "follow_up_question", "follow_up_trigger",
                "mandatory", and "importance".
        """
        self.questions = questions
        self.current_index = 0
        # Retry counts are tracked per question_id, not globally, so
        # struggling with one question doesn't eat into the retry
        # budget of unrelated questions later in the interview.
        self.retry_count: dict[str, int] = {}
        self.history: list[dict] = []
        self.completed = False

    def get_current_question(self) -> dict | None:
        """Return the question currently in focus.

        Returns:
            The question dict at current_index, or None if
            current_index is out of range (interview complete).
        """
        if 0 <= self.current_index < len(self.questions):
            return self.questions[self.current_index]
        return None

    def record_exchange(self, question_id: str, answer_text: str, stt_status: str) -> None:
        """Append a clean question/answer exchange to the history.

        This is only ever called from handle_response() once an
        answer has been classified as "valid", so self.history ends
        up containing only accepted exchanges — no retries or skips
        pollute it.

        Args:
            question_id: Identifier of the question being answered.
            answer_text: The candidate's answer text.
            stt_status: Status string from Day 24's stt_processor.

        Raises:
            ValueError: If stt_status is not one of
                VALID_STT_STATUSES. This is the runtime tripwire for
                a Day 24 contract misalignment — an unrecognized
                status string should fail loudly here rather than be
                recorded as if it were legitimate.
        """
        if stt_status not in VALID_STT_STATUSES:
            raise ValueError(f"Unknown stt_status: {stt_status!r}")
        self.history.append(
            {
                "question_id": question_id,
                "answer_text": answer_text,
                "stt_status": stt_status,
                "retry_count": self.retry_count.get(question_id, 0),
            }
        )

    def detect_issue(self, stt_status: str, answer_text: str) -> str:
        """Classify a candidate response for issues.

        Args:
            stt_status: Status string from Day 24's stt_processor.
            answer_text: The candidate's (possibly empty) answer text.

        Returns:
            "silence" if stt_status is "silence_detected",
            "poor_audio" if stt_status is "poor_audio_detected",
            "too_short" if the answer has fewer than 3 words,
            "valid" otherwise.
        """
        if stt_status == "silence_detected":
            return "silence"
        if stt_status == "poor_audio_detected":
            return "poor_audio"
        if len(answer_text.strip().split()) < 3:
            return "too_short"
        return "valid"

    def handle_response(self, stt_status: str, answer_text: str) -> str:
        """Process one candidate response and advance flow accordingly.

        Args:
            stt_status: Status string from Day 24's stt_processor.
            answer_text: The candidate's answer text.

        Returns:
            "retry" if the response had an issue and retries remain
                for this question (no advance).
            "skip" if the response had an issue and the retry budget
                for this question is exhausted (advances to the next
                question).
            "follow_up" if the response was valid and the current
                question's follow_up_trigger is set (advances).
            "next" if the response was valid and there is no
                follow-up trigger (advances).
        """
        issue = self.detect_issue(stt_status, answer_text)
        question = self.get_current_question()
        question_id = question.get("question_id") if question else None

        self.retry_count[question_id] = self.retry_count.get(question_id, 0) + 1

        if issue != "valid":
            if self.retry_count[question_id] <= MAX_RETRIES:
                logger.debug("Issue '%s' on question %s, retrying", issue, question_id)
                return "retry"
            logger.debug("Retry budget exhausted on question %s, skipping", question_id)
            self.advance()
            return "skip"

        self.record_exchange(question_id, answer_text, stt_status)
        follow_up_trigger = bool(question.get("follow_up_trigger")) if question else False
        self.advance()
        return "follow_up" if follow_up_trigger else "next"

    def advance(self) -> None:
        """Move to the next question, marking completion if exhausted."""
        self.current_index += 1
        if self.current_index >= len(self.questions):
            self.completed = True

    def is_complete(self) -> bool:
        """Return whether the interview has gone through all questions."""
        return self.completed

    def get_retry_message(self, issue: str) -> str:
        """Return a candidate-facing prompt for a given issue type.

        Args:
            issue: One of "silence", "poor_audio", "too_short", or any
                other value (falls back to a generic prompt).

        Returns:
            A message string appropriate to the detected issue.
        """
        messages = {
            "silence": "I didn't catch that, could you please respond?",
            "poor_audio": "The audio was unclear, could you repeat that?",
            "too_short": "Could you elaborate a little more?",
        }
        return messages.get(issue, "Could you please answer the question?")
