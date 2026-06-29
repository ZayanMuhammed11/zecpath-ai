"""
scripts/load_interview_question_bank.py

Standalone seed script — loads the HR interview question dataset from JSON,
builds an InterviewQuestionBank, and writes it to Redis.

Usage:
    python scripts/load_interview_question_bank.py

Requires Redis to be reachable via REDIS_URL in config/settings.py.
Mirrors the structure of scripts/load_question_bank.py exactly.
"""

import os
import sys

# Ensure the project root is on the Python path when run from any directory.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import redis as redis_lib

from api.redis_client import get_redis
from interview_ai.interview_models import InterviewPhase
from interview_ai.interview_question_bank import InterviewQuestionBankManager

# ── Configuration ─────────────────────────────────────────────────────────────

JOB_ID = "JOB-AUTOMOTIVE_QUALITY_ENGINEER"

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
QUESTIONS_FILE = os.path.join(PROJECT_ROOT, "data", "hr_interview_questions.json")

# ── Main ───────────────────────────────────────────────────────────────────────


def main() -> None:
    """
    Seed Redis with the HR Interview Question Bank.

    Steps:
    1. Connect to Redis via get_redis().
    2. Verify the connection with a ping — exit cleanly on failure.
    3. Load and validate questions from the JSON file.
    4. Build an InterviewQuestionBank for the Automotive Quality Engineer job.
    5. Save it to Redis.
    6. Print a structured confirmation report.
    """
    # 1. Redis connection
    redis_client = get_redis()

    # 2. Verify connection
    try:
        redis_client.ping()
    except redis_lib.ConnectionError as exc:
        print(f"[ERROR] Cannot connect to Redis: {exc}")
        sys.exit(1)

    manager = InterviewQuestionBankManager()

    # 3. Load questions from JSON
    questions = manager.load_from_file(QUESTIONS_FILE)

    # 4. Build InterviewQuestionBank
    bank = manager.build_question_bank(
        job_id=JOB_ID,
        questions=questions,
    )

    # 5. Save to Redis
    manager.save_to_redis(bank, redis_client)

    # 6. Confirmation report
    redis_key = f"interview_question_bank:{JOB_ID}"

    print("\n" + "=" * 60)
    print("  INTERVIEW QUESTION BANK LOADED SUCCESSFULLY")
    print("=" * 60)
    print(f"  Job ID      : {JOB_ID}")
    print(f"  Redis Key   : {redis_key}")
    print(f"  Total Qs    : {bank.total_questions}")
    print(f"  Version     : {bank.version}")
    print("-" * 60)
    print("  Questions per phase:")
    for phase in InterviewPhase:
        count = len([q for q in bank.questions if q.phase == phase])
        if count:
            print(f"    {phase.value:<30} {count}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
