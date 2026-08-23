"""
screening_ai/transcript_cleaner.py

Batch processor that wraps stt_processor.clean_transcript() for a full list
of Q&A audio inputs.  Output feeds into TranscriptStore.add_entry() downstream.
"""

from screening_ai.stt_processor import clean_transcript
from utils.logger import get_logger

logger = get_logger(__name__)


def process_audio_answers(audio_inputs: list[dict]) -> list[dict]:
    """Process a list of raw audio answer dicts through the STT cleaning pipeline.

    Each item in *audio_inputs* must contain:
        question_id (str)   — unique identifier for the question
        audio_text  (str)   — raw transcript text from the STT layer
        confidence  (float) — optional, defaults to 0.92

    Returns a list of dicts, one per input, each with:
        question_id (str)
        clean_text  (str)   — cleaned transcript, or "" on audio issues
        confidence  (float)
        status      (str)   — "processed" | "silence_detected" | "poor_audio_detected"
        issue       (str|None) — None | "silence" | "poor_audio"
    """
    logger.debug(
        "process_audio_answers called with %d input(s)", len(audio_inputs)
    )
    results: list[dict] = []

    for item in audio_inputs:
        question_id: str = item["question_id"]
        audio_text: str = item["audio_text"]
        confidence: float = item.get("confidence", 0.92)

        logger.debug(
            "process_audio_answers — processing question_id=%s", question_id
        )

        try:
            cleaned = clean_transcript(audio_text, confidence)
        except Exception as e:
            logger.error(
                "process_audio_answers — error on question_id=%s: %s",
                question_id,
                e,
            )
            raise

        results.append(
            {
                "question_id": question_id,
                "clean_text": cleaned["clean_text"],
                "confidence": cleaned["confidence"],
                "status": cleaned["status"],
                "issue": cleaned["issue"],
            }
        )

    logger.debug(
        "process_audio_answers complete — %d result(s) produced", len(results)
    )
    return results


def get_processing_summary(results: list[dict]) -> dict:
    """Return aggregate counts and a success rate for a batch of processed answers.

    Args:
        results: The list returned by process_audio_answers().

    Returns:
        A dict with keys:
            total               (int)   — number of items in the batch
            processed           (int)   — items with status "processed"
            silence_detected    (int)   — items with status "silence_detected"
            poor_audio_detected (int)   — items with status "poor_audio_detected"
            success_rate        (float) — processed / total * 100, rounded to 2 dp;
                                          0.0 when total is 0
    """
    logger.debug(
        "get_processing_summary called with %d result(s)", len(results)
    )
    total = len(results)
    processed = sum(1 for r in results if r["status"] == "processed")
    silence_detected = sum(
        1 for r in results if r["status"] == "silence_detected"
    )
    poor_audio_detected = sum(
        1 for r in results if r["status"] == "poor_audio_detected"
    )
    # DAY 42 FIX: Day 31 added noise_detected / language_mixed_detected
    # statuses to stt_processor.py, but this summary function was never
    # updated to count them — category counts silently didn't sum to total
    # whenever those two statuses occurred, even though success_rate itself
    # was still computed correctly.
    noise_detected = sum(1 for r in results if r["status"] == "noise_detected")
    language_mixed_detected = sum(
        1 for r in results if r["status"] == "language_mixed_detected"
    )
    success_rate = round(processed / total * 100, 2) if total > 0 else 0.0

    summary = {
        "total": total,
        "processed": processed,
        "silence_detected": silence_detected,
        "poor_audio_detected": poor_audio_detected,
        "noise_detected": noise_detected,
        "language_mixed_detected": language_mixed_detected,
        "success_rate": success_rate,
    }
    logger.debug("get_processing_summary result=%s", summary)
    return summary
