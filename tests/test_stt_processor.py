"""
tests/test_stt_processor.py

8 pytest tests for the Day 24 STT simulation + transcript cleaning layer.

No mocking required — no Redis or external calls are made by these modules.
"""

import pytest

from screening_ai.stt_processor import (
    clean_transcript,
    detect_silence,
    remove_fillers,
    handle_interruptions,
    fix_punctuation,
    detect_noise_markers,
    detect_language_mix,
    detect_audio_issue,
)
from screening_ai.transcript_cleaner import (
    process_audio_answers,
    get_processing_summary,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_batch() -> list[dict]:
    """Return a deterministic 3-item batch for batch-related tests."""
    return [
        {
            "question_id": "q1",
            "audio_text": "I have five years of Python experience.",
            "confidence": 0.95,
        },
        {
            "question_id": "q2",
            "audio_text": "",          # silence
            "confidence": 0.95,
        },
        {
            "question_id": "q3",
            "audio_text": "I worked on cloud infrastructure.",
            "confidence": 0.4,         # poor audio
        },
    ]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_clean_valid_input() -> None:
    """Normal sentence should return status 'processed' with non-empty clean_text."""
    result = clean_transcript("I have three years of software engineering experience")
    assert result["status"] == "processed", (
        f"Expected 'processed', got {result['status']!r}"
    )
    assert result["clean_text"], "clean_text should not be empty for valid input"
    assert result["issue"] is None


def test_filler_removal() -> None:
    """Filler words 'um' and 'uh' must be stripped from the transcript."""
    result = clean_transcript("um I have uh 3 years experience")
    clean = result["clean_text"].lower()
    assert "um" not in clean.split(), (
        f"'um' should have been removed but got: {clean!r}"
    )
    assert "uh" not in clean.split(), (
        f"'uh' should have been removed but got: {clean!r}"
    )
    assert result["status"] == "processed"


def test_silence_detection() -> None:
    """Empty string input must yield status 'silence_detected'."""
    result = clean_transcript("")
    assert result["status"] == "silence_detected", (
        f"Expected 'silence_detected', got {result['status']!r}"
    )
    assert result["clean_text"] == ""
    assert result["issue"] == "silence"


def test_poor_audio() -> None:
    """Confidence below threshold (0.4 < 0.6) must yield status 'poor_audio_detected'."""
    result = clean_transcript("I worked at Acme Corp", confidence=0.4)
    assert result["status"] == "poor_audio_detected", (
        f"Expected 'poor_audio_detected', got {result['status']!r}"
    )
    assert result["clean_text"] == ""
    assert result["issue"] == "poor_audio"


def test_punctuation_fix() -> None:
    """Transcript without a terminating punctuation mark must end with '.'."""
    result = clean_transcript("I enjoy working with distributed systems")
    assert result["status"] == "processed"
    assert result["clean_text"].endswith("."), (
        f"Expected trailing '.', got: {result['clean_text']!r}"
    )


def test_interruption_handling() -> None:
    """Repeated characters (e.g. 'yesssss') must be collapsed to a single char."""
    result = clean_transcript("yesssss I am available immediately")
    assert result["status"] == "processed"
    assert "sssss" not in result["clean_text"], (
        f"Repeated chars should be collapsed, got: {result['clean_text']!r}"
    )


def test_batch_processing() -> None:
    """process_audio_answers should return exactly one result per input."""
    batch = _make_batch()
    results = process_audio_answers(batch)
    assert len(results) == 3, f"Expected 3 results, got {len(results)}"
    # Verify required keys are present in every result
    required_keys = {"question_id", "clean_text", "confidence", "status", "issue"}
    for r in results:
        assert required_keys == required_keys & r.keys(), (
            f"Missing keys in result: {r}"
        )


def test_processing_summary() -> None:
    """get_processing_summary must return a dict with 'success_rate' and correct total."""
    batch = _make_batch()
    results = process_audio_answers(batch)
    summary = get_processing_summary(results)

    assert "success_rate" in summary, "'success_rate' key missing from summary"
    assert summary["total"] == 3, (
        f"Expected total=3, got {summary['total']}"
    )
    # Batch has 1 processed, 1 silence, 1 poor_audio
    assert summary["processed"] == 1
    assert summary["silence_detected"] == 1
    assert summary["poor_audio_detected"] == 1
    assert summary["success_rate"] == round(1 / 3 * 100, 2)


# ---------------------------------------------------------------------------
# Day 31 additions — noise / language-mix detection
# ---------------------------------------------------------------------------


def test_detect_noise_markers_positive() -> None:
    """A bracketed noise tag should be flagged as a noise marker."""
    result = detect_noise_markers("Can you hear me [inaudible] okay")
    assert result is True, f"Expected True, got {result}"


def test_detect_language_mix_positive() -> None:
    """Text with several non-Latin-script characters should flag a language mix."""
    result = detect_language_mix("मेरा अनुभव is good")
    assert result is True, f"Expected True, got {result}"


def test_detect_audio_issue_noise() -> None:
    """A punctuation-run artifact on otherwise high-confidence audio should classify as 'noise'."""
    result = detect_audio_issue("This is so noisy ????", 0.9)
    assert result == "noise", f"Expected 'noise', got {result!r}"


def test_detect_audio_issue_language_mix() -> None:
    """Non-Latin-script text on high-confidence audio should classify as 'language_mix'."""
    result = detect_audio_issue("मेरा अनुभव is good", 0.9)
    assert result == "language_mix", f"Expected 'language_mix', got {result!r}"
