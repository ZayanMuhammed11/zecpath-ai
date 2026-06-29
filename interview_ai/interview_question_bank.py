"""
interview_ai/interview_question_bank.py

InterviewQuestionBankManager — loads, builds, stores, and retrieves
HR interview question banks.
Part of Zecpath AI — Day 33, Sprint 4.

Redis key pattern : interview_question_bank:{job_id}  (no TTL)

DESIGN DECISION — redis_client parameter pattern:
redis_client is passed as a direct argument on the methods that need it
(save_to_redis, load_from_redis) rather than stored in __init__. This
makes the manager stateless, simplifies testing (callers pass MagicMock
at the call site, not at construction), and avoids carrying a live
connection object on an instance that may be reused across requests.
See interview_ai/DAY33_DECISIONS.md for full rationale.

DETERMINISM GUARANTEE:
No random module is imported or used anywhere in this file.
generate_interview_questions() produces identical output for identical
inputs on every call. Audit-trail reproducibility is guaranteed.
"""

import json
import os
from typing import List, Optional

from utils.logger import get_logger

from interview_ai.interview_models import (
    InterviewPhase,
    InterviewQuestion,
    InterviewQuestionBank,
    RoleLevel,
    RoleType,
)

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Module-level phase sort key
# ---------------------------------------------------------------------------

# Derived once at import time from the declaration order of InterviewPhase.
# Maps each phase to its 0-based index so generate_interview_questions can
# sort phases in definition order without string comparison or any randomness:
#   introduction=0, core_hr=1, role_based=2, closing=3
_PHASE_ORDER: dict[InterviewPhase, int] = {
    phase: idx for idx, phase in enumerate(InterviewPhase)
}


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------


class InterviewQuestionBankManager:
    """
    Manages the lifecycle of an HR interview question bank.

    Responsibilities:
    - Load and validate questions from a JSON data file
    - Build an InterviewQuestionBank wrapper with computed metadata
    - Persist and retrieve banks to/from Redis per job_id
    - Provide filtered, deterministically ordered views by phase and
      by candidate profile (role_level × role_type)

    Stateless by design — no instance state beyond the logger.
    redis_client is accepted as a direct parameter on the two methods
    that touch Redis (save_to_redis, load_from_redis).

    Redis key pattern : interview_question_bank:{job_id}
    Determinism       : all selection methods are side-effect-free and
                        produce the same output for the same input
                        every time. The random module is never used.
    """

    def load_from_file(self, filepath: str) -> List[InterviewQuestion]:
        """
        Load and validate interview questions from a JSON file.

        Reads the file at `filepath`, iterates over each JSON object, and
        constructs an InterviewQuestion via Pydantic v2 model validation.

        Unlike the screening_ai loader (which warns and skips invalid
        entries), this method raises immediately on the first invalid entry.
        A bad question in the bank is a configuration error that must be
        surfaced before any deployment or test run, not silently suppressed.

        Args:
            filepath: Absolute or relative path to the JSON question file.

        Returns:
            List of validated InterviewQuestion instances.

        Raises:
            FileNotFoundError : If the file does not exist at filepath.
            json.JSONDecodeError: If the file contains malformed JSON.
            ValueError         : If any entry fails Pydantic validation.
                                 The failing question_id is logged before
                                 the exception is raised.
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(
                f"Interview question file not found: {filepath}"
            )

        with open(filepath, "r", encoding="utf-8") as fh:
            raw_data: list = json.load(fh)

        questions: List[InterviewQuestion] = []
        for item in raw_data:
            try:
                question = InterviewQuestion(**item)
                questions.append(question)
            except Exception as exc:
                question_id = item.get("question_id", "UNKNOWN")
                logger.error(
                    "Validation failed for interview question '%s': %s",
                    question_id,
                    exc,
                )
                raise ValueError(
                    f"Interview question '{question_id}' failed validation: {exc}"
                ) from exc

        logger.info(
            "Loaded %d interview questions from '%s'.",
            len(questions),
            filepath,
        )
        return questions

    def build_question_bank(
        self,
        job_id: str,
        questions: List[InterviewQuestion],
    ) -> InterviewQuestionBank:
        """
        Wrap a validated list of InterviewQuestion objects into an
        InterviewQuestionBank with computed metadata.

        Args:
            job_id    : Unique job identifier used as the Redis key suffix.
            questions : Validated list of InterviewQuestion instances.

        Returns:
            A fully populated InterviewQuestionBank instance.
        """
        bank = InterviewQuestionBank(
            job_id=job_id,
            questions=questions,
            total_questions=len(questions),
        )

        logger.info(
            "Built InterviewQuestionBank for job_id='%s' with %d total questions.",
            job_id,
            bank.total_questions,
        )
        return bank

    def save_to_redis(
        self,
        bank: InterviewQuestionBank,
        redis_client,
    ) -> None:
        """
        Serialize an InterviewQuestionBank and write it to Redis.

        Key format : interview_question_bank:{job_id}
        TTL        : none — the bank persists until explicitly deleted.

        Args:
            bank         : The InterviewQuestionBank instance to persist.
            redis_client : An active Redis connection (redis.Redis instance).
        """
        redis_key = f"interview_question_bank:{bank.job_id}"
        serialized = bank.model_dump_json()
        redis_client.set(redis_key, serialized)
        logger.info(
            "Saved InterviewQuestionBank to Redis key='%s' (%d questions).",
            redis_key,
            bank.total_questions,
        )

    def load_from_redis(
        self,
        job_id: str,
        redis_client,
    ) -> Optional[InterviewQuestionBank]:
        """
        Retrieve and deserialize an InterviewQuestionBank from Redis.

        Args:
            job_id       : The job identifier whose bank should be loaded.
            redis_client : An active Redis connection (redis.Redis instance).

        Returns:
            InterviewQuestionBank if the key exists and deserializes
            successfully, otherwise None.
        """
        redis_key = f"interview_question_bank:{job_id}"
        raw = redis_client.get(redis_key)

        if raw is None:
            logger.warning(
                "No InterviewQuestionBank found in Redis for key='%s'.",
                redis_key,
            )
            return None

        try:
            bank = InterviewQuestionBank.model_validate_json(raw)
            logger.info(
                "Loaded InterviewQuestionBank from Redis key='%s' (%d questions).",
                redis_key,
                bank.total_questions,
            )
            return bank
        except Exception as exc:
            logger.error(
                "Failed to deserialize InterviewQuestionBank for key='%s': %s",
                redis_key,
                exc,
            )
            return None

    def get_questions_by_phase(
        self,
        bank: InterviewQuestionBank,
        phase: InterviewPhase,
    ) -> List[InterviewQuestion]:
        """
        Return all questions in the bank that belong to the specified phase,
        sorted ascending by their `order` field.

        Args:
            bank  : The InterviewQuestionBank to filter.
            phase : The InterviewPhase to match.

        Returns:
            Deterministically sorted list of InterviewQuestion for the
            given phase.
        """
        filtered = [q for q in bank.questions if q.phase == phase]
        return sorted(filtered, key=lambda q: q.order)

    def generate_interview_questions(
        self,
        bank: InterviewQuestionBank,
        role_level: RoleLevel,
        role_type: RoleType,
    ) -> List[InterviewQuestion]:
        """
        Generate a deterministic, ordered list of interview questions for a
        specific candidate profile (role_level × role_type).

        Inclusion criteria — a question is included when BOTH hold:
            1. role_level is in q.applicable_levels
               OR RoleLevel.all_levels is in q.applicable_levels
            2. role_type is in q.applicable_role_types

        Sort order (two-key, fully deterministic):
            Primary   — _PHASE_ORDER[q.phase] ascending
                        (introduction=0, core_hr=1, role_based=2, closing=3)
            Secondary — q.order ascending within each phase

        Determinism guarantee:
            The random module is never imported or used in this file.
            Calling this method twice with identical arguments always
            produces identical output — same question objects, same
            sequence. Required for test reproducibility and audit trail.

        Args:
            bank       : The InterviewQuestionBank to draw from.
            role_level : The candidate's resolved seniority level.
            role_type  : The interview track (technical or non_technical).

        Returns:
            Deterministically ordered List[InterviewQuestion] matching
            the candidate's profile.
        """
        filtered = [
            q
            for q in bank.questions
            if (
                role_level in q.applicable_levels
                or RoleLevel.all_levels in q.applicable_levels
            )
            and role_type in q.applicable_role_types
        ]

        ordered = sorted(
            filtered,
            key=lambda q: (_PHASE_ORDER[q.phase], q.order),
        )

        logger.info(
            "generate_interview_questions: role_level='%s', role_type='%s' "
            "-> %d questions selected.",
            role_level.value,
            role_type.value,
            len(ordered),
        )
        return ordered
