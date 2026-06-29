"""
screening_ai/question_bank.py

QuestionBankManager — loads, builds, stores, and retrieves question banks.
Part of Zecpath AI — Day 22, Sprint 2.

Redis key pattern: question_bank:{job_id}  (no TTL)
"""

import json
import os
from datetime import datetime, timezone
from typing import List, Optional

from utils.logger import get_logger

from screening_ai.question_models import (
    QuestionBank,
    QuestionCategory,
    RoleLevel,
    ScreeningQuestion,
)


class QuestionBankManager:
    """
    Manages the lifecycle of a QE screening question bank.

    Responsibilities:
    - Load questions from a JSON file and validate each against ScreeningQuestion
    - Build a QuestionBank object with computed metadata
    - Persist and retrieve QuestionBank to/from Redis per job_id
    - Provide filtered views: by category, by level, by mandatory flag, by question_id

    Redis key pattern: question_bank:{job_id}
    """

    def __init__(self, redis_client) -> None:
        """
        Initialise the manager with a Redis client.

        Args:
            redis_client: An active Redis connection (redis.Redis instance).
        """
        self.r = redis_client
        self.logger = get_logger(__name__)

    def load_from_file(self, file_path: str) -> List[ScreeningQuestion]:
        """
        Load and validate screening questions from a JSON file.

        Reads the file at file_path, iterates over each JSON object,
        and constructs a ScreeningQuestion via Pydantic validation.
        Any item that fails validation is skipped with a logged warning.

        Args:
            file_path: Absolute or relative path to the JSON question file.

        Returns:
            List of validated ScreeningQuestion instances.

        Raises:
            FileNotFoundError: If the file does not exist at file_path.
            json.JSONDecodeError: If the file contains malformed JSON.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Question file not found: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            raw_data: list = json.load(f)

        questions: List[ScreeningQuestion] = []
        for item in raw_data:
            try:
                question = ScreeningQuestion(**item)
                questions.append(question)
            except Exception as exc:
                self.logger.warning(
                    "Skipping invalid question entry '%s': %s",
                    item.get("question_id", "UNKNOWN"),
                    exc,
                )

        self.logger.info(
            "Loaded %d questions from '%s'", len(questions), file_path
        )
        return questions

    def build_question_bank(
        self,
        job_id: str,
        job_title: str,
        domain: str,
        questions: List[ScreeningQuestion],
    ) -> QuestionBank:
        """
        Construct a QuestionBank from a validated list of ScreeningQuestion objects.

        Automatically computes total_questions and the unique set of categories
        present in the supplied question list.

        Args:
            job_id:     Unique job identifier used as the Redis key suffix.
            job_title:  Human-readable title, e.g. "Automotive Quality Engineer".
            domain:     QE sub-domain, e.g. "automotive_manufacturing".
            questions:  Validated list of ScreeningQuestion instances.

        Returns:
            A fully populated QuestionBank instance.
        """
        unique_categories: List[str] = list(
            dict.fromkeys(q.category.value for q in questions)
        )

        bank = QuestionBank(
            job_id=job_id,
            job_title=job_title,
            domain=domain,
            total_questions=len(questions),
            categories=unique_categories,
            questions=questions,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        self.logger.info(
            "Built QuestionBank for job_id='%s' with %d questions across %d categories.",
            job_id,
            bank.total_questions,
            len(bank.categories),
        )
        return bank

    def save_to_redis(self, bank: QuestionBank) -> None:
        """
        Serialize a QuestionBank and write it to Redis.

        Key format: question_bank:{job_id}
        No TTL is applied — the bank persists until explicitly deleted.

        Args:
            bank: The QuestionBank instance to persist.
        """
        redis_key = f"question_bank:{bank.job_id}"
        serialized = bank.model_dump_json()
        self.r.set(redis_key, serialized)
        self.logger.info(
            "Saved QuestionBank to Redis key='%s' (%d questions).",
            redis_key,
            bank.total_questions,
        )

    def load_from_redis(self, job_id: str) -> Optional[QuestionBank]:
        """
        Retrieve and deserialize a QuestionBank from Redis.

        Args:
            job_id: The job identifier whose bank should be loaded.

        Returns:
            QuestionBank if the key exists and deserializes successfully,
            otherwise None.
        """
        redis_key = f"question_bank:{job_id}"
        raw = self.r.get(redis_key)

        if raw is None:
            self.logger.warning(
                "No QuestionBank found in Redis for key='%s'.", redis_key
            )
            return None

        try:
            bank = QuestionBank.model_validate_json(raw)
            self.logger.info(
                "Loaded QuestionBank from Redis key='%s' (%d questions).",
                redis_key,
                bank.total_questions,
            )
            return bank
        except Exception as exc:
            self.logger.error(
                "Failed to deserialize QuestionBank for key='%s': %s",
                redis_key,
                exc,
            )
            return None

    def get_questions_by_category(
        self, job_id: str, category: str
    ) -> List[ScreeningQuestion]:
        """
        Return all questions in a bank that belong to the specified category.

        Args:
            job_id:   Job identifier to load the bank from Redis.
            category: Category string matching a QuestionCategory value,
                      e.g. "skills", "experience".

        Returns:
            Filtered list of ScreeningQuestion, or empty list if bank not found.
        """
        bank = self.load_from_redis(job_id)
        if bank is None:
            return []

        return [q for q in bank.questions if q.category.value == category]

    def get_questions_by_level(
        self, job_id: str, level: str
    ) -> List[ScreeningQuestion]:
        """
        Return questions applicable to a given role level.

        Includes questions tagged all_levels as well as those explicitly
        tagged with the requested level. Excludes questions tagged only
        for a different level.

        Args:
            job_id: Job identifier to load the bank from Redis.
            level:  Role level string, e.g. "fresher", "mid", "senior".

        Returns:
            Filtered list of ScreeningQuestion, or empty list if bank not found.
        """
        bank = self.load_from_redis(job_id)
        if bank is None:
            return []

        return [
            q for q in bank.questions
            if RoleLevel.all_levels in q.applicable_levels
            or level in [lvl.value for lvl in q.applicable_levels]
        ]

    def get_mandatory_questions(self, job_id: str) -> List[ScreeningQuestion]:
        """
        Return only the mandatory questions from a bank.

        Args:
            job_id: Job identifier to load the bank from Redis.

        Returns:
            List of mandatory ScreeningQuestion, or empty list if bank not found.
        """
        bank = self.load_from_redis(job_id)
        if bank is None:
            return []

        return [q for q in bank.questions if q.mandatory]

    def get_question_by_id(
        self, job_id: str, question_id: str
    ) -> Optional[ScreeningQuestion]:
        """
        Find and return a single question by its unique question_id.

        Args:
            job_id:      Job identifier to load the bank from Redis.
            question_id: The exact question_id string, e.g. "Q_SKILL_001".

        Returns:
            The matching ScreeningQuestion, or None if not found.
        """
        bank = self.load_from_redis(job_id)
        if bank is None:
            return None

        for question in bank.questions:
            if question.question_id == question_id:
                return question

        self.logger.warning(
            "Question '%s' not found in bank for job_id='%s'.",
            question_id,
            job_id,
        )
        return None
