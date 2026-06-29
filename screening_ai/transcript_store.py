"""
Redis-backed store for AI screening call transcripts.

Handles the full lifecycle of ScreeningTranscript objects:
  - create_transcript  — initialise and persist a new transcript
  - add_entry          — append a question-answer exchange and recompute metrics
  - complete_transcript — mark a session finished and stamp completion time
  - get_transcript     — retrieve and deserialise a transcript from Redis

Also exposes two pure-function helpers used when building entries:
  - normalize_answer      — clean raw STT output
  - detect_answer_quality — classify quality against expected keywords
  - detect_keywords       — find which expected keywords appear in an answer

Redis key pattern: transcript:{candidate_id}:{job_id}
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import List, Optional

from screening_ai.transcript_models import (
    AnswerQuality,
    ScreeningTranscript,
    TranscriptEntry,
    TranscriptStatus,
)
from utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Module-level filler word constants
# ---------------------------------------------------------------------------

# Multi-word phrases must be removed before single-word fillers so that
# "you know" is caught as a unit rather than leaving orphan "you" / "know".
_FILLER_PHRASES: List[str] = ["you know"]
_FILLER_WORDS: List[str] = ["um", "uh", "hmm", "like", "basically", "actually"]


class TranscriptStore:
    """
    Manages persistence and retrieval of ScreeningTranscript objects in Redis.

    All read operations use ``redis.get()`` with safe None-checks so the caller
    always receives a typed result (ScreeningTranscript) or None — never raw
    bytes or an unchecked deserialisation error.

    Normalization and quality-detection methods are pure functions:
    they hold no state and are fully testable in isolation.
    """

    def __init__(self, redis_client) -> None:
        """
        Initialise the store with an active Redis client.

        Args:
            redis_client: A ``redis.Redis`` instance or a compatible test mock.
        """
        self._redis = redis_client
        logger.info("TranscriptStore initialized.")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _redis_key(candidate_id: str, job_id: str) -> str:
        """Build the canonical Redis key for a transcript.

        Args:
            candidate_id: Identifier of the candidate.
            job_id: Identifier of the job role.

        Returns:
            Redis key string in format ``transcript:{candidate_id}:{job_id}``.
        """
        return f"transcript:{candidate_id}:{job_id}"

    # ------------------------------------------------------------------
    # Lifecycle operations
    # ------------------------------------------------------------------

    def create_transcript(
        self,
        candidate_id: str,
        job_id: str,
        language: str = "en",
    ) -> ScreeningTranscript:
        """
        Create a new in-progress transcript and persist it to Redis immediately.

        The transcript ID follows the format ``TRX-{candidate_id}-{job_id}``,
        consistent with the established key-naming conventions of this platform.

        Args:
            candidate_id: Identifier of the candidate being screened.
            job_id: Identifier of the job role being screened for.
            language: BCP-47 language code for the screening call.

        Returns:
            The newly created and persisted ScreeningTranscript.
        """
        transcript = ScreeningTranscript(
            transcript_id=f"TRX-{candidate_id}-{job_id}",
            candidate_id=candidate_id,
            job_id=job_id,
            language=language,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        key = self._redis_key(candidate_id, job_id)
        self._redis.set(key, transcript.model_dump_json())
        logger.info(
            "Created transcript %s -> Redis key: %s",
            transcript.transcript_id,
            key,
        )
        return transcript

    def add_entry(
        self,
        candidate_id: str,
        job_id: str,
        entry: TranscriptEntry,
    ) -> Optional[ScreeningTranscript]:
        """
        Append a TranscriptEntry to an existing transcript and recompute metrics.

        After appending the entry, ``total_questions_asked``,
        ``overall_confidence``, and ``total_duration_seconds`` are all
        recomputed from the full entries list before saving back to Redis.

        Args:
            candidate_id: Identifier of the candidate.
            job_id: Identifier of the job role.
            entry: The populated TranscriptEntry to append.

        Returns:
            The updated ScreeningTranscript, or None if the transcript was
            not found in Redis.
        """
        transcript = self.get_transcript(candidate_id, job_id)
        if transcript is None:
            logger.warning(
                "add_entry: transcript not found — candidate=%s job=%s",
                candidate_id,
                job_id,
            )
            return None

        transcript.entries.append(entry)
        transcript.total_questions_asked = len(transcript.entries)
        transcript.overall_confidence = transcript.compute_overall_confidence()
        transcript.total_duration_seconds = transcript.compute_total_duration()

        key = self._redis_key(candidate_id, job_id)
        self._redis.set(key, transcript.model_dump_json())
        logger.info(
            "Added entry %s to transcript %s (total entries: %d)",
            entry.question_id,
            transcript.transcript_id,
            len(transcript.entries),
        )
        return transcript

    def complete_transcript(
        self,
        candidate_id: str,
        job_id: str,
    ) -> Optional[ScreeningTranscript]:
        """
        Mark a transcript as completed and stamp the UTC completion time.

        Recomputes overall confidence and total duration one final time
        before persisting, ensuring metrics are accurate at close.

        Args:
            candidate_id: Identifier of the candidate.
            job_id: Identifier of the job role.

        Returns:
            The updated ScreeningTranscript with status ``completed``, or
            None if the transcript was not found in Redis.
        """
        transcript = self.get_transcript(candidate_id, job_id)
        if transcript is None:
            logger.warning(
                "complete_transcript: transcript not found — candidate=%s job=%s",
                candidate_id,
                job_id,
            )
            return None

        transcript.status = TranscriptStatus.completed
        transcript.completed_at = datetime.now(timezone.utc).isoformat()
        transcript.overall_confidence = transcript.compute_overall_confidence()
        transcript.total_duration_seconds = transcript.compute_total_duration()

        key = self._redis_key(candidate_id, job_id)
        self._redis.set(key, transcript.model_dump_json())
        logger.info(
            "Completed transcript %s at %s",
            transcript.transcript_id,
            transcript.completed_at,
        )
        return transcript

    def get_transcript(
        self,
        candidate_id: str,
        job_id: str,
    ) -> Optional[ScreeningTranscript]:
        """
        Retrieve and deserialise a transcript from Redis.

        Args:
            candidate_id: Identifier of the candidate.
            job_id: Identifier of the job role.

        Returns:
            The deserialised ScreeningTranscript, or None if the Redis key
            does not exist.
        """
        key = self._redis_key(candidate_id, job_id)
        raw = self._redis.get(key)
        if raw is None:
            logger.debug("get_transcript: key not found — %s", key)
            return None
        return ScreeningTranscript.model_validate_json(raw)

    # ------------------------------------------------------------------
    # STT normalization
    # ------------------------------------------------------------------

    def normalize_answer(self, raw_answer: str) -> str:
        """
        Clean raw speech-to-text output into normalized answer text.

        This method should always be called *before* ``detect_answer_quality``
        so that quality detection always operates on clean input.

        Steps applied in order:

        1. Return ``""`` immediately for blank/whitespace-only input.
        2. Lowercase the entire string.
        3. Remove filler phrases (e.g. ``"you know"``) using whole-word matching.
        4. Remove filler words (``um``, ``uh``, ``hmm``, ``like``,
           ``basically``, ``actually``) using whole-word matching.
        5. Collapse multiple whitespace characters into a single space and strip.
        6. Return ``""`` if the result is now empty (e.g. input was all fillers).
        7. Capitalize the first character.
        8. Append a period if the string does not end with ``.``, ``!``, or ``?``.

        Args:
            raw_answer: Raw STT transcript string.

        Returns:
            Cleaned, normalized answer string, or ``""`` for empty/filler-only input.
        """
        if not raw_answer.strip():
            return ""

        text: str = raw_answer.lower()

        # Step 3 — remove multi-word filler phrases first
        for phrase in _FILLER_PHRASES:
            text = re.sub(r"\b" + re.escape(phrase) + r"\b", " ", text)

        # Step 4 — remove single-word fillers
        single_word_pattern = (
            r"\b(" + "|".join(re.escape(w) for w in _FILLER_WORDS) + r")\b"
        )
        text = re.sub(single_word_pattern, " ", text)

        # Step 5 — collapse whitespace
        text = re.sub(r"\s+", " ", text).strip()

        # Step 6 — guard: all fillers, nothing left
        if not text:
            return ""

        # Step 7 — capitalize first letter
        text = text[0].upper() + text[1:]

        # Step 8 — add terminal punctuation if missing
        if text[-1] not in (".", "!", "?"):
            text += "."

        return text

    # ------------------------------------------------------------------
    # Quality and keyword detection
    # ------------------------------------------------------------------

    def detect_answer_quality(
        self,
        answer_text: str,
        expected_keywords: List[str],
    ) -> AnswerQuality:
        """
        Classify the quality of an answer using priority-ordered rules.

        Rules are evaluated in strict priority order; the first match wins:

        1. ``len(answer_text.strip()) == 0`` → ``no_answer``
        2. ``len(answer_text.split()) < 3``  → ``too_short``
        3. ``expected_keywords`` is non-empty AND no keyword detected → ``off_topic``
        4. ``len(answer_text.split()) < 8``  → ``basic``
        5. Otherwise                          → ``good``

        Rule 3 only fires when ``expected_keywords`` is non-empty; if no
        keywords are defined for a question, off_topic can never be returned.

        Args:
            answer_text: Normalized answer string (post-``normalize_answer``).
            expected_keywords: Domain keywords expected in a strong answer.
                               Pass an empty list if no keywords are defined.

        Returns:
            The appropriate ``AnswerQuality`` enum value.
        """
        stripped = answer_text.strip()

        if not stripped:
            return AnswerQuality.no_answer

        words = stripped.split()

        if len(words) < 3:
            return AnswerQuality.too_short

        if expected_keywords:
            matched = self.detect_keywords(stripped, expected_keywords)
            if not matched:
                return AnswerQuality.off_topic

        if len(words) < 8:
            return AnswerQuality.basic

        return AnswerQuality.good

    def detect_keywords(
        self,
        answer_text: str,
        expected_keywords: List[str],
    ) -> List[str]:
        """
        Find which expected keywords or phrases appear in the answer.

        Matching is case-insensitive and uses substring search, so
        multi-word keywords (e.g. ``"root cause"``, ``"control plan"``)
        are handled correctly.

        Args:
            answer_text: The candidate's (normalized) answer text.
            expected_keywords: Keywords or phrases to search for.

        Returns:
            List of items from ``expected_keywords`` that were found in
            ``answer_text``, preserving the original casing of the keyword.
        """
        lower_answer = answer_text.lower()
        return [kw for kw in expected_keywords if kw.lower() in lower_answer]
