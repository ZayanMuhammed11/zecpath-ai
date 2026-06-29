"""
screening_ai/stt_processor.py

STT simulation and pre-cleaning pipeline for the Zecpath screening system.
Runs BEFORE TranscriptStore.normalize_answer() in the processing chain.
"""

import re
from utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FILLER_WORDS = ["um", "uh", "like", "you know", "hmm", "basically", "actually"]
STT_CONFIDENCE_THRESHOLD = 0.6  # below this = poor_audio
MIN_VALID_WORD_COUNT = 2


# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------


def speech_to_text(audio_input: str) -> dict:
    """Simulated STT layer. Replace with Whisper/Google STT API call in production."""
    logger.debug("speech_to_text called with input length=%d", len(audio_input))
    result = {
        "text": audio_input,
        "confidence": 0.92,
        "language": "en",
    }
    logger.debug("speech_to_text returning confidence=%.2f", result["confidence"])
    return result


def detect_silence(text: str) -> bool:
    """Return True if the text is empty or too short to be a valid answer.

    A response with fewer than 2 stripped characters is treated as silence.
    """
    logger.debug("detect_silence called with text=%r", text)
    return len(text.strip()) < MIN_VALID_WORD_COUNT


def remove_fillers(text: str) -> str:
    """Remove common speech filler words from the transcript using word-boundary matching.

    Iterates over FILLER_WORDS and strips each one case-insensitively, then
    collapses any runs of whitespace left behind.
    """
    logger.debug("remove_fillers called")
    result = text
    for word in FILLER_WORDS:
        result = re.sub(rf"\b{re.escape(word)}\b", "", result, flags=re.IGNORECASE)
    # Collapse internal whitespace created by removals
    result = re.sub(r"[ \t]+", " ", result).strip()
    logger.debug("remove_fillers result=%r", result)
    return result


def handle_interruptions(text: str) -> str:
    """Collapse character repetitions of 3 or more down to a single character.

    Handles common STT artefacts such as "yesssss" → "yes" or "hmmmm" → "hm".
    """
    logger.debug("handle_interruptions called")
    result = re.sub(r"(.)\1{2,}", r"\1", text)
    logger.debug("handle_interruptions result=%r", result)
    return result


def fix_punctuation(text: str) -> str:
    """Strip surrounding whitespace, capitalise the first character, and ensure
    the text ends with a sentence-terminating punctuation mark (. ! ?).

    Does nothing to text that is already properly terminated.
    """
    logger.debug("fix_punctuation called")
    result = text.strip()
    if result:
        result = result[0].upper() + result[1:]
        if not result.endswith((".", "!", "?")):
            result += "."
    logger.debug("fix_punctuation result=%r", result)
    return result


def detect_audio_issue(text: str, confidence: float) -> str:
    """Classify an STT result as 'silence', 'poor_audio', or 'valid'.

    Checks silence first (empty/blank input), then confidence threshold.

    Args:
        text: The raw transcript text from STT.
        confidence: The STT confidence score (0.0 – 1.0).

    Returns:
        One of the strings: "silence" | "poor_audio" | "valid".
    """
    logger.debug(
        "detect_audio_issue called with text=%r, confidence=%.2f", text, confidence
    )
    if detect_silence(text):
        logger.debug("detect_audio_issue → silence")
        return "silence"
    if confidence < STT_CONFIDENCE_THRESHOLD:
        logger.debug(
            "detect_audio_issue → poor_audio (confidence=%.2f < threshold=%.2f)",
            confidence,
            STT_CONFIDENCE_THRESHOLD,
        )
        return "poor_audio"
    logger.debug("detect_audio_issue → valid")
    return "valid"


def clean_transcript(audio_input: str, confidence: float = 0.92) -> dict:
    """Run the full STT pre-cleaning pipeline on a single audio input.

    Pipeline steps (in order):
        1. detect_audio_issue  — gate on silence / poor audio
        2. remove_fillers      — strip um, uh, like, etc.
        3. handle_interruptions — collapse character repetitions
        4. fix_punctuation     — capitalise + terminate

    Args:
        audio_input: Raw text output from the STT layer.
        confidence:  STT confidence score (default 0.92).

    Returns:
        A dict with keys:
            clean_text  — processed transcript (empty string on issues)
            confidence  — echo of the input confidence
            status      — "processed" | "silence_detected" | "poor_audio_detected"
            issue       — None | "silence" | "poor_audio"
    """
    logger.debug(
        "clean_transcript entry — input=%r, confidence=%.2f", audio_input, confidence
    )

    issue = detect_audio_issue(audio_input, confidence)

    if issue == "silence":
        result = {
            "clean_text": "",
            "confidence": confidence,
            "status": "silence_detected",
            "issue": "silence",
        }
        logger.debug("clean_transcript exit — status=silence_detected")
        return result

    if issue == "poor_audio":
        result = {
            "clean_text": "",
            "confidence": confidence,
            "status": "poor_audio_detected",
            "issue": "poor_audio",
        }
        logger.debug("clean_transcript exit — status=poor_audio_detected")
        return result

    # Valid audio — run through cleaning chain
    text = remove_fillers(audio_input)
    text = handle_interruptions(text)
    text = fix_punctuation(text)

    result = {
        "clean_text": text,
        "confidence": confidence,
        "status": "processed",
        "issue": None,
    }
    logger.debug("clean_transcript exit — status=processed, clean_text=%r", text)
    return result
