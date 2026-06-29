"""
scripts/load_question_bank.py

Standalone seed script — loads the QE question dataset from JSON,
builds a QuestionBank, and writes it to Redis.

Usage:
    python scripts/load_question_bank.py

Requires Redis to be running on localhost:6379 (Docker).
"""

import os
import sys

# Ensure the project root is on the Python path when run from any directory.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import redis

from screening_ai.question_bank import QuestionBankManager

# ── Configuration ─────────────────────────────────────────────────────────────

JOB_ID = "JOB-AUTOMOTIVE_QUALITY_ENGINEER"
JOB_TITLE = "Automotive Quality Engineer"
DOMAIN = "automotive_manufacturing"

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
QUESTIONS_FILE = os.path.join(PROJECT_ROOT, "data", "qe_screening_questions.json")

# ── Main ───────────────────────────────────────────────────────────────────────


def main() -> None:
    """
    Seed Redis with the QE Screening Question Bank.

    Steps:
    1. Connect to Redis.
    2. Load and validate questions from the JSON file.
    3. Build a QuestionBank for the Automotive Quality Engineer job.
    4. Save it to Redis.
    5. Print a structured confirmation report.
    """
    # 1. Redis connection
    redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)
    try:
        redis_client.ping()
    except redis.ConnectionError as exc:
        print(f"[ERROR] Cannot connect to Redis: {exc}")
        sys.exit(1)

    manager = QuestionBankManager(redis_client=redis_client)

    # 2. Load questions from JSON
    questions = manager.load_from_file(QUESTIONS_FILE)

    # 3. Build QuestionBank
    bank = manager.build_question_bank(
        job_id=JOB_ID,
        job_title=JOB_TITLE,
        domain=DOMAIN,
        questions=questions,
    )

    # 4. Save to Redis
    manager.save_to_redis(bank)

    # 5. Confirmation report
    redis_key = f"question_bank:{JOB_ID}"
    mandatory_count = len([q for q in bank.questions if q.mandatory])

    print("\n" + "=" * 60)
    print("  QUESTION BANK LOADED SUCCESSFULLY")
    print("=" * 60)
    print(f"  Job ID     : {JOB_ID}")
    print(f"  Job Title  : {JOB_TITLE}")
    print(f"  Domain     : {DOMAIN}")
    print(f"  Redis Key  : {redis_key}")
    print(f"  Total Qs   : {bank.total_questions}")
    print(f"  Mandatory  : {mandatory_count}")
    print(f"  Created At : {bank.created_at}")
    print("-" * 60)
    print("  Questions per category:")
    for category in bank.categories:
        count = len([q for q in bank.questions if q.category.value == category])
        print(f"    {category:<20} {count}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
