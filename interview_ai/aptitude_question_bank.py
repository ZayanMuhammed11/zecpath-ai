"""
interview_ai/aptitude_question_bank.py

AptitudeQuestionBankManager — loads, builds, and retrieves aptitude
question banks.
Part of Zecpath AI — Day 38, Sprint 4.

DESIGN DECISION — storage layer:
File-based only, mirroring the interim treatment used for other Day 33
storage-layer choices. Redis persistence for aptitude question banks is
a deferred Sprint 3 backlog item — see interview_ai/DAY38_DECISIONS.md.

DETERMINISM GUARANTEE:
No random module is imported or used anywhere in this file. All lookup
and filter methods produce identical output for identical inputs on
every call.
"""

import json
import os
from typing import List, Optional

from utils.logger import get_logger

from interview_ai.aptitude_models import (
    AptitudeCategory,
    AptitudeQuestion,
    AptitudeQuestionBank,
)

logger = get_logger(__name__)


class AptitudeQuestionBankManager:
    """
    Manages the lifecycle of an aptitude question bank.

    Responsibilities:
    - Load and validate questions from a JSON data file
    - Build an AptitudeQuestionBank wrapper
    - Provide filtered, deterministic views by category and by question_id

    Stateless by design — no instance state beyond the logger. Mirrors
    InterviewQuestionBankManager's shape and method-naming conventions,
    adapted for AptitudeQuestionBank.
    """

    def load_from_file(self, filepath: str) -> AptitudeQuestionBank:
        """
        Load and validate aptitude questions from a JSON file and wrap
        them into an AptitudeQuestionBank.

        Reads the file at `filepath`, iterates over each JSON object, and
        constructs an AptitudeQuestion via Pydantic v2 model validation.
        Raises immediately on the first invalid entry — a bad question in
        the bank is a configuration error that must be surfaced before
        any deployment or test run, not silently suppressed.

        Args:
            filepath: Absolute or relative path to the JSON question file.

        Returns:
            A fully populated AptitudeQuestionBank instance. The job_id
            is derived from the JSON file's base name (without extension).

        Raises:
            FileNotFoundError : If the file does not exist at filepath.
            json.JSONDecodeError: If the file contains malformed JSON.
            ValueError         : If any entry fails Pydantic validation.
                                 The failing question_id is logged before
                                 the exception is raised.
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(
                f"Aptitude question file not found: {filepath}"
            )

        with open(filepath, "r", encoding="utf-8") as fh:
            raw_data: list = json.load(fh)

        questions: List[AptitudeQuestion] = []
        for item in raw_data:
            try:
                question = AptitudeQuestion(**item)
                questions.append(question)
            except Exception as exc:
                question_id = item.get("question_id", "UNKNOWN")
                logger.error(
                    "Validation failed for aptitude question '%s': %s",
                    question_id,
                    exc,
                )
                raise ValueError(
                    f"Aptitude question '{question_id}' failed validation: {exc}"
                ) from exc

        job_id = os.path.splitext(os.path.basename(filepath))[0]
        bank = self.build_question_bank(job_id=job_id, questions=questions)

        logger.info(
            "Loaded %d aptitude questions from '%s'.",
            len(questions),
            filepath,
        )
        return bank

    def build_question_bank(
        self,
        job_id: str,
        questions: List[AptitudeQuestion],
    ) -> AptitudeQuestionBank:
        """
        Wrap a validated list of AptitudeQuestion objects into an
        AptitudeQuestionBank.

        Args:
            job_id    : Unique job identifier associated with this bank.
            questions : Validated list of AptitudeQuestion instances.

        Returns:
            A fully populated AptitudeQuestionBank instance.
        """
        bank = AptitudeQuestionBank(job_id=job_id, questions=questions)

        logger.info(
            "Built AptitudeQuestionBank for job_id='%s' with %d total questions.",
            job_id,
            len(bank.questions),
        )
        return bank

    def get_questions_by_category(
        self,
        bank: AptitudeQuestionBank,
        category: AptitudeCategory,
    ) -> List[AptitudeQuestion]:
        """
        Return all questions in the bank that belong to the specified
        category.

        Args:
            bank     : The AptitudeQuestionBank to filter.
            category : The AptitudeCategory to match.

        Returns:
            List of AptitudeQuestion matching the given category, in
            bank order (deterministic, no sorting/randomization applied).
        """
        filtered = [q for q in bank.questions if q.category == category]
        logger.debug(
            "get_questions_by_category: category='%s' -> %d questions.",
            category.value,
            len(filtered),
        )
        return filtered

    def get_question_by_id(
        self,
        bank: AptitudeQuestionBank,
        question_id: str,
    ) -> Optional[AptitudeQuestion]:
        """
        Look up a single question in the bank by its question_id.

        Args:
            bank        : The AptitudeQuestionBank to search.
            question_id : The unique question_id to find.

        Returns:
            The matching AptitudeQuestion if found, otherwise None.
        """
        for question in bank.questions:
            if question.question_id == question_id:
                return question
        logger.warning(
            "get_question_by_id: no question found for question_id='%s'.",
            question_id,
        )
        return None
