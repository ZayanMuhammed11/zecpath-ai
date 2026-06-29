"""
Unit tests for TranscriptStore — Day 23.

Redis is fully mocked using MagicMock; no live connection is required.
The mock captures serialized values written via ``set()`` and replays them
from ``get()``, mirroring the pattern established in the Day 21 and Day 22
test suites.

Test inventory:
    1. test_create_transcript           — correct ID format, in_progress status, empty entries
    2. test_add_entry                   — entry appended, total_questions_asked updated
    3. test_complete_transcript         — status=completed, completed_at populated
    4. test_get_transcript_missing      — Redis miss → None returned
    5. test_normalize_answer_removes_fillers — filler removal, capitalization, period
    6. test_normalize_answer_empty      — empty / whitespace-only input → ""
    7. test_detect_answer_quality_good  — long answer with keywords → good
    8. test_detect_keywords             — partial keyword match, absent keyword excluded
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from screening_ai.transcript_models import (
    AnswerQuality,
    TranscriptEntry,
    TranscriptStatus,
)
from screening_ai.transcript_store import TranscriptStore


# ---------------------------------------------------------------------------
# Shared fixture factory
# ---------------------------------------------------------------------------


def _make_store() -> tuple[TranscriptStore, dict[str, str]]:
    """
    Build a TranscriptStore backed by an in-memory MagicMock Redis client.

    ``set(key, value)`` writes into ``redis_store``.
    ``get(key)`` reads from ``redis_store``, returning None for missing keys.

    Returns:
        A 2-tuple of (store, redis_store) so individual tests can seed or
        inspect the underlying dict if needed.
    """
    redis_store: dict[str, str] = {}

    mock_redis = MagicMock()
    mock_redis.set.side_effect = lambda key, value: redis_store.update({key: value})
    mock_redis.get.side_effect = lambda key: redis_store.get(key)

    store = TranscriptStore(redis_client=mock_redis)
    return store, redis_store


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_create_transcript() -> None:
    """
    create_transcript must return a ScreeningTranscript whose transcript_id
    follows the ``TRX-{candidate_id}-{job_id}`` format, whose status is
    ``in_progress``, and whose entries list is empty.
    """
    store, _ = _make_store()

    transcript = store.create_transcript("C001", "JOB-001")

    assert transcript.transcript_id == "TRX-C001-JOB-001"
    assert transcript.status == TranscriptStatus.in_progress
    assert transcript.entries == []
    assert transcript.candidate_id == "C001"
    assert transcript.job_id == "JOB-001"
    assert transcript.created_at != ""


def test_add_entry() -> None:
    """
    add_entry must append the entry and set total_questions_asked to 1
    after a single addition.
    """
    store, _ = _make_store()
    store.create_transcript("C002", "JOB-002")

    entry = TranscriptEntry(
        question_id="Q_TEST_001",
        question_text="Tell me about yourself.",
        answer_text="I have five years of experience in quality assurance testing.",
        confidence_score=0.90,
        duration_seconds=12,
    )
    updated = store.add_entry("C002", "JOB-002", entry)

    assert updated is not None
    assert len(updated.entries) == 1
    assert updated.total_questions_asked == 1
    assert updated.entries[0].question_id == "Q_TEST_001"


def test_complete_transcript() -> None:
    """
    complete_transcript must set status to ``completed`` and populate
    ``completed_at`` with a non-empty timestamp string.
    """
    store, _ = _make_store()
    store.create_transcript("C003", "JOB-003")

    completed = store.complete_transcript("C003", "JOB-003")

    assert completed is not None
    assert completed.status == TranscriptStatus.completed
    assert completed.completed_at != ""


def test_get_transcript_missing() -> None:
    """
    get_transcript must return None when the Redis key does not exist,
    without raising any exception.
    """
    store, _ = _make_store()

    result = store.get_transcript("C999", "JOB-DOES-NOT-EXIST")

    assert result is None


def test_normalize_answer_removes_fillers() -> None:
    """
    normalize_answer must strip filler words (``um``, ``uh``), capitalize
    the first character, and append a period when terminal punctuation is absent.
    """
    store, _ = _make_store()

    raw = "um uh I have experience"
    result = store.normalize_answer(raw)

    # Fillers gone
    words = result.lower().split()
    assert "um" not in words
    assert "uh" not in words

    # Meaningful content preserved
    assert "experience" in result.lower()

    # Formatting rules applied
    assert result[0].isupper(), "First character must be uppercase"
    assert result.endswith("."), "Must end with a period"


def test_normalize_answer_empty() -> None:
    """
    normalize_answer must return an empty string for both an empty string
    and a whitespace-only string, without raising any exception.
    """
    store, _ = _make_store()

    assert store.normalize_answer("") == ""
    assert store.normalize_answer("   ") == ""


def test_detect_answer_quality_good() -> None:
    """
    A sufficiently long answer that contains expected keywords must be
    classified as ``good``.
    """
    store, _ = _make_store()

    answer = (
        "I have hands on experience with FMEA APQP PPAP and control plans "
        "also worked with SPC and IATF 16949 for several years."
    )
    keywords = ["FMEA", "APQP", "PPAP", "SPC"]

    quality = store.detect_answer_quality(answer, keywords)

    assert quality == AnswerQuality.good


def test_detect_keywords() -> None:
    """
    detect_keywords must return only the subset of expected keywords that
    actually appear in the answer text (case-insensitive), excluding those
    that are absent.
    """
    store, _ = _make_store()

    answer = (
        "I used root cause analysis and implemented corrective actions via 8D methodology."
    )
    expected = ["root cause", "corrective", "8D", "CAPA", "analysis"]

    matched = store.detect_keywords(answer, expected)

    assert "root cause" in matched
    assert "corrective" in matched
    assert "8D" in matched
    assert "analysis" in matched
    assert "CAPA" not in matched  # absent from answer
