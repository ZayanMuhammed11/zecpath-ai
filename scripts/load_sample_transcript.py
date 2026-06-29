"""
Demo script: load a complete sample transcript for candidate C011.

Creates a screening transcript for JOB-AUTOMOTIVE_QUALITY_ENGINEER, adds
three realistic question-answer entries (with full normalization and quality
detection applied), marks the session complete, then prints a structured
summary including the Redis key written.

Usage (from project root, venv ``zecc`` active):

    python scripts/load_sample_transcript.py
"""

from __future__ import annotations

import os
import sys

# Allow imports from the project root regardless of invocation directory.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import redis

from screening_ai.transcript_models import TranscriptEntry
from screening_ai.transcript_store import TranscriptStore

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CANDIDATE_ID = "C011"
JOB_ID = "JOB-AUTOMOTIVE_QUALITY_ENGINEER"

REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0

# ---------------------------------------------------------------------------
# Raw entry definitions
# Raw STT text is normalized inside main() via store.normalize_answer().
# ---------------------------------------------------------------------------

_RAW_ENTRIES = [
    {
        "question_id": "Q_INTRO_001",
        "question_text": (
            "Could you briefly introduce yourself and your professional background?"
        ),
        "raw_answer": (
            "um I have worked in quality engineering for about 8 years mainly in "
            "automotive sector at companies like Ashok Leyland and Bharat Forge"
        ),
        "confidence_score": 0.93,
        "expected_keywords": [],
        "start_time": "00:00:05",
        "end_time": "00:00:18",
        "duration_seconds": 13,
    },
    {
        "question_id": "Q_SKILL_001",
        "question_text": (
            "Which QE methodologies are you familiar with — "
            "FMEA, APQP, PPAP, or Control Plans?"
        ),
        "raw_answer": (
            "uh I have hands on experience with FMEA APQP PPAP and control plans "
            "also worked with SPC and IATF 16949"
        ),
        "confidence_score": 0.91,
        "expected_keywords": ["FMEA", "APQP", "PPAP", "control plan", "SPC", "MSA"],
        "start_time": "00:00:20",
        "end_time": "00:00:35",
        "duration_seconds": 15,
    },
    {
        "question_id": "Q_EXP_004",
        "question_text": (
            "Can you describe a quality problem you identified and how you resolved it?"
        ),
        "raw_answer": (
            "we had a defect issue in welding process I used 8D methodology and "
            "root cause analysis to identify the problem and implemented corrective actions"
        ),
        "confidence_score": 0.88,
        "expected_keywords": ["root cause", "corrective", "8D", "CAPA", "analysis"],
        "start_time": "00:00:37",
        "end_time": "00:01:02",
        "duration_seconds": 25,
    },
]


def main() -> None:
    """Run the sample transcript load and print a full summary."""
    # 1. Connect to Redis
    r = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        decode_responses=True,
    )
    store = TranscriptStore(redis_client=r)

    # 2. Create transcript
    transcript = store.create_transcript(CANDIDATE_ID, JOB_ID)
    print(f"\n{'=' * 60}")
    print(f"  Created : {transcript.transcript_id}")
    print(f"  Status  : {transcript.status.value}")
    print(f"{'=' * 60}\n")

    # 3. Normalize, detect quality/keywords, build and add each entry
    for raw in _RAW_ENTRIES:
        normalized: str = store.normalize_answer(raw["raw_answer"])
        quality = store.detect_answer_quality(normalized, raw["expected_keywords"])
        keywords = store.detect_keywords(normalized, raw["expected_keywords"])

        entry = TranscriptEntry(
            question_id=raw["question_id"],
            question_text=raw["question_text"],
            answer_text=normalized,
            answer_quality=quality,
            confidence_score=raw["confidence_score"],
            keywords_detected=keywords,
            start_time=raw["start_time"],
            end_time=raw["end_time"],
            duration_seconds=raw["duration_seconds"],
        )
        store.add_entry(CANDIDATE_ID, JOB_ID, entry)
        print(
            f"  [{raw['question_id']}]  quality={quality.value!s:<12}  "
            f"keywords={keywords}"
        )

    # 4. Complete the transcript
    completed = store.complete_transcript(CANDIDATE_ID, JOB_ID)
    if completed is None:
        print("\n  ERROR: complete_transcript returned None — transcript not found.\n")
        return

    # 5. Print full summary
    redis_key = f"transcript:{CANDIDATE_ID}:{JOB_ID}"

    print(f"\n{'=' * 60}")
    print("  TRANSCRIPT SUMMARY")
    print(f"{'=' * 60}")
    print(f"  transcript_id        : {completed.transcript_id}")
    print(f"  status               : {completed.status.value}")
    print(f"  total_questions_asked: {completed.total_questions_asked}")
    print(f"  overall_confidence   : {completed.overall_confidence:.4f}")
    print(f"  total_duration_secs  : {completed.total_duration_seconds}s")
    print(f"  completed_at         : {completed.completed_at}")
    print(f"\n  Entries:")
    for entry in completed.entries:
        print(f"    [{entry.question_id}]")
        print(f"      answer_quality      : {entry.answer_quality.value}")
        print(f"      keywords_detected   : {entry.keywords_detected}")
        print(f"      follow_up_triggered : {entry.follow_up_triggered}")
    print(f"\n  Redis key written    : {redis_key}")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
