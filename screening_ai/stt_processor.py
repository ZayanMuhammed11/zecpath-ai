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

# Bracketed STT artifact tags (e.g. "[noise]", "[background]", "[inaudible]")
# are treated generically as noise markers — any non-empty bracketed segment,
# not just those three examples, since STT vendors emit a variety of
# bracketed event tags and hardcoding the list would miss new ones.
NOISE_TAG_PATTERN = re.compile(r"\[[^\[\]]+\]")

# 4+ consecutive non-alphanumeric, non-whitespace characters (e.g. "????",
# "!!!!") — a common STT artifact when background noise gets transcribed as
# punctuation-like garbage.
NOISE_PUNCTUATION_RUN_PATTERN = re.compile(r"[^\w\s]{4,}")

# Ratio of non-alphabetic characters (excluding whitespace) above which text
# is considered noisy, even without bracket tags or punctuation runs.
NOISE_NON_ALPHA_RATIO_THRESHOLD = 0.4

# Generic "any non-Latin script block present" check rather than hardcoding
# to one language's Unicode range — covers Greek, Cyrillic, Hebrew, Arabic,
# Devanagari, Thai, Hiragana/Katakana, CJK, and Hangul in one pattern so
# language-mix detection isn't tied to a single expected non-English language.
NON_LATIN_SCRIPT_PATTERN = re.compile(
    r"[\u0370-\u03FF\u0400-\u04FF\u0590-\u05FF\u0600-\u06FF"
    r"\u0900-\u097F\u0E00-\u0E7F\u3040-\u30FF\u4E00-\u9FFF\uAC00-\uD7AF]"
)
NON_LATIN_CHAR_COUNT_THRESHOLD = 2


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


# KEY DECISION: noise is judged on TEXT artifacts only in this simulation
# layer — real audio-level noise detection (e.g. spectral analysis) is out
# of scope until real STT integration.
def detect_noise_markers(text: str) -> bool:
    """Return True if the text contains background-noise STT artifacts.

    Three independent signals are checked, any one of which is sufficient:
        - a bracketed noise tag (e.g. "[noise]", "[background]", "[inaudible]")
        - 4 or more consecutive non-alphanumeric, non-whitespace characters
          (e.g. "????", "!!!!")
        - a ratio of non-alphabetic characters (excluding whitespace) above
          40% of the text's non-whitespace length

    Args:
        text: The raw transcript text from STT.

    Returns:
        True if any noise signal is present, False otherwise.
    """
    logger.debug("detect_noise_markers called with text=%r", text)

    if NOISE_TAG_PATTERN.search(text):
        logger.debug("detect_noise_markers → True (bracketed noise tag)")
        return True

    if NOISE_PUNCTUATION_RUN_PATTERN.search(text):
        logger.debug("detect_noise_markers → True (punctuation run)")
        return True

    non_whitespace = re.sub(r"\s+", "", text)
    if non_whitespace:
        non_alpha_count = sum(1 for ch in non_whitespace if not ch.isalpha())
        ratio = non_alpha_count / len(non_whitespace)
        if ratio > NOISE_NON_ALPHA_RATIO_THRESHOLD:
            logger.debug("detect_noise_markers → True (non_alpha_ratio=%.2f)", ratio)
            return True

    logger.debug("detect_noise_markers → False")
    return False


# KEY DECISION: this is a coarse script-level check, not true language
# identification — sufficient for the simulation layer; real STT/language-
# detection APIs will replace this in production.
def detect_language_mix(text: str, expected_language: str = "en") -> bool:
    """Return True if the text contains a meaningful proportion of non-Latin-script characters.

    Only checks when expected_language == "en" (the only screening language
    currently supported); any other expected_language short-circuits to
    False rather than guessing at script expectations it has no data for.

    Args:
        text: The raw transcript text from STT.
        expected_language: The language the candidate was expected to answer
            in. Defaults to "en".

    Returns:
        True if more than 2 non-Latin-script characters are found and
        expected_language == "en", False otherwise.
    """
    logger.debug(
        "detect_language_mix called with text=%r, expected_language=%r",
        text,
        expected_language,
    )
    if expected_language != "en":
        logger.debug("detect_language_mix → False (expected_language != 'en')")
        return False

    non_latin_chars = NON_LATIN_SCRIPT_PATTERN.findall(text)
    result = len(non_latin_chars) > NON_LATIN_CHAR_COUNT_THRESHOLD
    logger.debug(
        "detect_language_mix → %s (non_latin_char_count=%d)",
        result,
        len(non_latin_chars),
    )
    return result


def detect_audio_issue(text: str, confidence: float) -> str:
    """Classify an STT result as 'silence', 'language_mix', 'noise', 'poor_audio', or 'valid'.

    Checks silence first (empty/blank input), then language mixing and noise
    markers (both text-content issues independent of STT confidence), then
    the confidence threshold.

    Args:
        text: The raw transcript text from STT.
        confidence: The STT confidence score (0.0 – 1.0).

    Returns:
        One of the strings: "silence" | "language_mix" | "noise" | "poor_audio" | "valid".
    """
    logger.debug(
        "detect_audio_issue called with text=%r, confidence=%.2f", text, confidence
    )
    if detect_silence(text):
        logger.debug("detect_audio_issue → silence")
        return "silence"
    # KEY DECISION: language_mix and noise are checked BEFORE the confidence
    # threshold because both can occur on high-confidence STT output — they
    # are text-content issues, not transcription-confidence issues, so
    # gating them on confidence would miss real cases.
    if detect_language_mix(text):
        logger.debug("detect_audio_issue → language_mix")
        return "language_mix"
    if detect_noise_markers(text):
        logger.debug("detect_audio_issue → noise")
        return "noise"
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
        1. detect_audio_issue  — gate on silence / language_mix / noise / poor audio
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
            status      — "processed" | "silence_detected" | "language_mixed_detected" |
                          "noise_detected" | "poor_audio_detected"
            issue       — None | "silence" | "language_mix" | "noise" | "poor_audio"
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

    if issue == "language_mix":
        result = {
            "clean_text": "",
            "confidence": confidence,
            "status": "language_mixed_detected",
            "issue": "language_mix",
        }
        logger.debug("clean_transcript exit — status=language_mixed_detected")
        return result

    if issue == "noise":
        result = {
            "clean_text": "",
            "confidence": confidence,
            "status": "noise_detected",
            "issue": "noise",
        }
        logger.debug("clean_transcript exit — status=noise_detected")
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
