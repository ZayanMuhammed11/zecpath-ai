"""
technical_ai/technical_question_bank.py

TechnicalQuestionBankManager — loads, builds, and retrieves technical
interview question banks.
Part of Zecpath AI — Day 46.

DESIGN DECISION — storage layer:
File-based only, no Redis anywhere in this module. This mirrors the
Day 38 aptitude_question_bank.py precedent (interview_ai/aptitude_question_bank.py),
not the Redis-backed pattern used by InterviewQuestionBankManager. See
technical_ai/DAY46_DECISIONS.md for full rationale.

DETERMINISM GUARANTEE:
No random module is imported or used anywhere in this file.
generate_interview_questions() produces identical output for identical
inputs on every call.
"""

import json
import os
from typing import List

from utils.logger import get_logger

from technical_ai.technical_interview_models import (
    TechnicalInterviewPhase,
    TechnicalInterviewQuestion,
    TechnicalInterviewQuestionBank,
    TechnicalSkillDomain,
    TechnicalDifficulty,
)

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Module-level phase sort key
# ---------------------------------------------------------------------------

# Derived once at import time from the declaration order of
# TechnicalInterviewPhase. Maps each phase to its 0-based index so
# generate_interview_questions can sort phases in definition order without
# string comparison or any randomness:
#   introduction=0, experience_based=1, conceptual=2, scenario_based=3,
#   closing=4
_PHASE_ORDER: dict[TechnicalInterviewPhase, int] = {
    phase: idx for idx, phase in enumerate(TechnicalInterviewPhase)
}


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------


class TechnicalQuestionBankManager:
    """
    Manages the lifecycle of a technical interview question bank.

    Responsibilities:
    - Load and validate questions from a JSON data file
    - Build a TechnicalInterviewQuestionBank wrapper scoped to one
      skill_domain
    - Provide filtered, deterministically ordered views by phase and by
      candidate difficulty tier

    Stateless by design — no instance state beyond the module-level
    logger, mirroring InterviewQuestionBankManager's shape.

    No Redis in this module — file-based only.
    Determinism: all selection methods are side-effect-free and produce
    the same output for the same input every time. The random module is
    never used.
    """

    def load_from_file(self, filepath: str) -> List[TechnicalInterviewQuestion]:
        """
        Load and validate technical interview questions from a JSON file.

        Reads the file at `filepath`, iterates over each JSON object, and
        constructs a TechnicalInterviewQuestion via Pydantic v2 model
        validation. Raises immediately on the first invalid entry.

        Returns a flat list (like InterviewQuestionBankManager.load_from_file),
        NOT a pre-wrapped bank — job_id and skill_domain are not knowable
        from question content alone (a single question file may span
        multiple domains).

        Args:
            filepath: Absolute or relative path to the JSON question file.

        Returns:
            List of validated TechnicalInterviewQuestion instances.

        Raises:
            FileNotFoundError : If the file does not exist at filepath.
            json.JSONDecodeError: If the file contains malformed JSON.
            ValueError         : If any entry fails Pydantic validation.
                                 The failing question_id is logged before
                                 the exception is raised.
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(
                f"Technical question file not found: {filepath}"
            )

        with open(filepath, "r", encoding="utf-8") as fh:
            raw_data: list = json.load(fh)

        questions: List[TechnicalInterviewQuestion] = []
        for item in raw_data:
            try:
                question = TechnicalInterviewQuestion(**item)
                questions.append(question)
            except Exception as exc:
                question_id = item.get("question_id", "UNKNOWN")
                logger.error(
                    "Validation failed for technical question '%s': %s",
                    question_id,
                    exc,
                )
                raise ValueError(
                    f"Technical question '{question_id}' failed validation: {exc}"
                ) from exc

        logger.info(
            "Loaded %d technical questions from '%s'.",
            len(questions),
            filepath,
        )
        return questions

    def build_question_bank(
        self,
        job_id: str,
        skill_domain: TechnicalSkillDomain,
        questions: List[TechnicalInterviewQuestion],
    ) -> TechnicalInterviewQuestionBank:
        """
        Wrap a validated list of TechnicalInterviewQuestion objects into a
        TechnicalInterviewQuestionBank scoped to a single skill_domain.

        A bank must be internally consistent: every question's
        skill_domain must match the bank's skill_domain argument. This
        guards against loading a mixed-domain JSON file and building a
        bank for the wrong domain.

        Args:
            job_id       : Unique job identifier used for this bank.
            skill_domain : The single QE sector domain this bank is
                           scoped to.
            questions    : Validated list of TechnicalInterviewQuestion
                           instances.

        Returns:
            A fully populated TechnicalInterviewQuestionBank instance.

        Raises:
            ValueError: If any question's skill_domain does not match
                        `skill_domain`. The error message lists the
                        mismatched question_ids.
        """
        mismatched = [
            q.question_id for q in questions if q.skill_domain != skill_domain
        ]
        if mismatched:
            raise ValueError(
                f"build_question_bank: skill_domain mismatch for job_id="
                f"'{job_id}', expected '{skill_domain.value}'. Mismatched "
                f"question_ids: {mismatched}"
            )

        bank = TechnicalInterviewQuestionBank(
            job_id=job_id,
            skill_domain=skill_domain,
            questions=questions,
            total_questions=len(questions),
        )

        logger.info(
            "Built TechnicalInterviewQuestionBank for job_id='%s', "
            "skill_domain='%s' with %d total questions.",
            job_id,
            skill_domain.value,
            bank.total_questions,
        )
        return bank

    def get_questions_by_phase(
        self,
        bank: TechnicalInterviewQuestionBank,
        phase: TechnicalInterviewPhase,
    ) -> List[TechnicalInterviewQuestion]:
        """
        Return all questions in the bank that belong to the specified
        phase, sorted ascending by their `order` field.

        Args:
            bank  : The TechnicalInterviewQuestionBank to filter.
            phase : The TechnicalInterviewPhase to match.

        Returns:
            Deterministically sorted list of TechnicalInterviewQuestion
            for the given phase.
        """
        filtered = [q for q in bank.questions if q.phase == phase]
        return sorted(filtered, key=lambda q: q.order)

    def generate_interview_questions(
        self,
        bank: TechnicalInterviewQuestionBank,
        difficulty: TechnicalDifficulty,
    ) -> List[TechnicalInterviewQuestion]:
        """
        Generate a deterministic, ordered list of technical interview
        questions for a specific candidate difficulty tier.

        Inclusion criteria:
            difficulty in q.applicable_difficulties

        Sort order (two-key, fully deterministic):
            Primary   — _PHASE_ORDER[q.phase] ascending
                        (introduction=0, experience_based=1, conceptual=2,
                        scenario_based=3, closing=4)
            Secondary — q.order ascending within each phase

        Determinism guarantee:
            The random module is never imported or used in this file.
            Calling this method twice with identical arguments always
            produces identical output — same question objects, same
            sequence.

        Args:
            bank       : The TechnicalInterviewQuestionBank to draw from.
            difficulty : The candidate's resolved technical difficulty tier.

        Returns:
            Deterministically ordered List[TechnicalInterviewQuestion]
            matching the requested difficulty.
        """
        filtered = [
            q for q in bank.questions if difficulty in q.applicable_difficulties
        ]

        ordered = sorted(
            filtered,
            key=lambda q: (_PHASE_ORDER[q.phase], q.order),
        )

        logger.info(
            "generate_interview_questions: difficulty='%s' -> %d "
            "questions selected.",
            difficulty.value,
            len(ordered),
        )
        return ordered
