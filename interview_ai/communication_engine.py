"""
interview_ai/communication_engine.py

Communication skill evaluation engine for the Zecpath interview_ai module.

Receives already-cleaned candidate answer text (plain Python string output of
the STT pre-cleaning pipeline) and returns a 0–100 communication quality score.
Evaluates HOW something was said — fluency, grammar, vocabulary, clarity,
structure, and filler density — never WHAT was said or whether it was relevant.

Fully isolated: does not import from screening_ai/, ats_engine/, or scoring/.
No I/O, no Redis, no random module usage — pure deterministic computation.
"""

import re

from interview_ai.communication_models import CommunicationScore, CommunicationScoreBreakdown
from utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Duplicated from screening_ai/stt_processor.py BY VALUE — never by import.
# interview_ai/ is a fully isolated module; sharing imports across module
# boundaries is prohibited by project convention.
FILLER_WORDS: list[str] = [
    "um",
    "uh",
    "like",
    "you know",
    "hmm",
    "basically",
    "actually",
]

STRUCTURE_KEYWORDS: list[str] = [
    "because",
    "for example",
    "as a result",
    "therefore",
    "first",
    "then",
    "finally",
    "however",
    "additionally",
]


# ---------------------------------------------------------------------------
# Public scoring functions
# ---------------------------------------------------------------------------


def score_fluency(text: str) -> float:
    """Score the fluency of an answer based on valid sentence count.

    Splits text on sentence-terminating punctuation (.!?) and counts fragments
    containing more than 3 words as "valid sentences."

    Args:
        text: Cleaned candidate answer text.

    Returns:
        1.0 for 2 or more valid sentences, 0.6 for exactly 1, 0.3 for 0.
    """
    logger.debug("score_fluency called with text=%r", text)
    fragments = re.split(r"[.!?]", text)
    valid_count = sum(1 for f in fragments if len(f.split()) > 3)
    if valid_count >= 2:
        return 1.0
    if valid_count == 1:
        return 0.6
    return 0.3


def score_grammar(text: str) -> float:
    """Score grammar quality using capitalization, terminal punctuation, and sentence length.

    Combines two independent heuristic factors weighted equally:

    factor_a (capitalization_and_terminal_punctuation):
        - 1.0 if the stripped text starts with an uppercase letter AND ends
          with '.', '!', or '?'.
        - 0.5 if exactly one of those conditions is true.
        - 0.0 if neither is true.

    factor_b (sentence_length_quality):
        - Splits text on [.!?], discards empty fragments, computes average
          word count per remaining fragment (avg_words).
        - 1.0 for avg_words in [4, 25] (inclusive).
        - 0.6 for avg_words in [2, 4) or (25, 40].
        - 0.3 for avg_words < 2 or > 40.

    Args:
        text: Cleaned candidate answer text.

    Returns:
        round(factor_a * 0.5 + factor_b * 0.5, 4), a float in [0.0, 1.0].
    """
    logger.debug("score_grammar called with text=%r", text)
    stripped = text.strip()

    # factor_a: capitalisation and terminal punctuation
    starts_upper: bool = bool(stripped) and stripped[0].isupper()
    ends_terminal: bool = stripped.endswith((".", "!", "?"))
    conditions_met: int = int(starts_upper) + int(ends_terminal)
    if conditions_met == 2:
        factor_a = 1.0
    elif conditions_met == 1:
        factor_a = 0.5
    else:
        factor_a = 0.0

    # factor_b: sentence length quality
    fragments = [f for f in re.split(r"[.!?]", text) if f.strip()]
    if not fragments:
        avg_words: float = 0.0
    else:
        avg_words = sum(len(f.split()) for f in fragments) / len(fragments)

    if 4 <= avg_words <= 25:
        factor_b = 1.0
    elif (2 <= avg_words < 4) or (25 < avg_words <= 40):
        factor_b = 0.6
    else:
        factor_b = 0.3

    result = round(factor_a * 0.5 + factor_b * 0.5, 4)
    logger.debug(
        "score_grammar → %.4f (factor_a=%.1f, factor_b=%.1f, avg_words=%.2f)",
        result,
        factor_a,
        factor_b,
        avg_words,
    )
    return result


def score_vocabulary(text: str) -> float:
    """Score vocabulary richness using the ratio of unique to total words.

    Short answers (fewer than 4 words) are capped at 0.5 to prevent trivially
    unique short responses from achieving a perfect vocabulary score.

    For all word counts the ratio is computed first using three bands, then for
    word_count < 4 the result is clamped to min(0.5, ratio_score).

    Args:
        text: Cleaned candidate answer text.

    Returns:
        A float in [0.0, 1.0] (short answers capped at 0.5).
    """
    logger.debug("score_vocabulary called with text=%r", text)
    words: list[str] = text.lower().split()
    word_count: int = len(words)

    if word_count == 0:
        return 0.0

    unique_ratio: float = len(set(words)) / word_count
    if unique_ratio >= 0.6:
        ratio_score = 1.0
    elif unique_ratio >= 0.4:
        ratio_score = 0.7
    else:
        ratio_score = 0.4

    if word_count < 4:
        result = min(0.5, ratio_score)
        logger.debug(
            "score_vocabulary → %.1f (short-answer cap applied, ratio=%.2f)",
            result,
            unique_ratio,
        )
        return result

    logger.debug("score_vocabulary → %.1f (ratio=%.2f)", ratio_score, unique_ratio)
    return ratio_score


def score_clarity(text: str) -> float:
    """Score clarity based on answer length in words.

    Longer answers are interpreted as more complete and better developed
    responses.

    Args:
        text: Cleaned candidate answer text.

    Returns:
        1.0 for more than 12 words, 0.7 for more than 6, 0.4 otherwise.
    """
    logger.debug("score_clarity called with text=%r", text)
    length: int = len(text.split())
    if length > 12:
        return 1.0
    if length > 6:
        return 0.7
    return 0.4


def score_structure(text: str) -> float:
    """Score structural quality using discourse marker and connective keyword detection.

    Presence of at least one STRUCTURE_KEYWORDS entry signals organised,
    multi-part reasoning.

    Args:
        text: Cleaned candidate answer text.

    Returns:
        1.0 if any structure keyword is found, 0.6 for long answers (>10 words)
        without one, 0.3 otherwise.
    """
    logger.debug("score_structure called with text=%r", text)
    text_lower: str = text.lower()
    if any(keyword in text_lower for keyword in STRUCTURE_KEYWORDS):
        return 1.0
    if len(text.split()) > 10:
        return 0.6
    return 0.3


def filler_penalty(text: str) -> float:
    """Compute a deduction based on filler-word density in the text.

    Uses word-boundary regex matching to avoid partial-word false positives
    (e.g. "like" inside "likewise" is not counted). Multi-word fillers such as
    "you know" are matched as a phrase. Penalty is capped at 0.5.

    Args:
        text: Cleaned candidate answer text.

    Returns:
        A float in [0.0, 0.5] rounded to 4 decimal places.
    """
    logger.debug("filler_penalty called with text=%r", text)
    text_lower: str = text.lower()
    count: int = 0
    for word in FILLER_WORDS:
        pattern = r"\b" + re.escape(word) + r"\b"
        count += len(re.findall(pattern, text_lower))
    penalty = min(count * 0.1, 0.5)
    result = round(penalty, 4)
    logger.debug("filler_penalty → %.4f (filler_count=%d)", result, count)
    return result


def get_communication_level(score: float) -> str:
    """Map a numeric communication score to a qualitative level label.

    Args:
        score: Communication score in the range [0.0, 100.0].

    Returns:
        One of "Excellent" (>=85), "Good" (>=70), "Average" (>=50), or "Poor".
    """
    if score >= 85:
        return "Excellent"
    if score >= 70:
        return "Good"
    if score >= 50:
        return "Average"
    return "Poor"


def calculate_communication_score(text: str) -> CommunicationScore:
    """Run the full communication evaluation pipeline on a cleaned answer string.

    Pipeline (applied only to non-empty input):
        1. score_fluency      — valid sentence count
        2. score_grammar      — capitalisation, punctuation, sentence length
        3. score_vocabulary   — unique-word ratio
        4. score_clarity      — total word count bands
        5. score_structure    — discourse marker detection
        6. filler_penalty     — filler-word deduction

    Weighted average:
        weighted = (fluency + grammar + vocabulary + clarity + structure) * 0.2
        final    = max(weighted - penalty, 0.0)
        score    = round(final * 100, 2)

    Returns a zero CommunicationScore (all fields 0.0, level "Poor") without
    invoking any sub-scorers when input is None, empty, or whitespace-only.

    Args:
        text: Cleaned candidate answer text (output of the STT pre-cleaning
            pipeline). May be None, empty, or whitespace-only.

    Returns:
        A fully populated CommunicationScore Pydantic model instance.
    """
    logger.debug("calculate_communication_score called with text=%r", text)

    if not text or not text.strip():
        logger.warning(
            "calculate_communication_score received empty or whitespace-only text; "
            "returning zero score without invoking sub-scorers."
        )
        return CommunicationScore(
            communication_score=0.0,
            level="Poor",
            word_count=0,
            breakdown=CommunicationScoreBreakdown(
                fluency=0.0,
                grammar=0.0,
                vocabulary=0.0,
                clarity=0.0,
                structure=0.0,
                filler_penalty=0.0,
            ),
        )

    word_count: int = len(text.split())
    fluency: float = score_fluency(text)
    grammar: float = score_grammar(text)
    vocabulary: float = score_vocabulary(text)
    clarity: float = score_clarity(text)
    structure: float = score_structure(text)
    penalty: float = filler_penalty(text)

    weighted: float = (
        fluency * 0.2
        + grammar * 0.2
        + vocabulary * 0.2
        + clarity * 0.2
        + structure * 0.2
    )
    final: float = max(weighted - penalty, 0.0)
    communication_score: float = round(final * 100, 2)
    level: str = get_communication_level(communication_score)

    logger.info(
        "calculate_communication_score ->cx score=%.2f, level=%s, word_count=%d",
        communication_score,
        level,
        word_count,
    )

    return CommunicationScore(
        communication_score=communication_score,
        level=level,
        word_count=word_count,
        breakdown=CommunicationScoreBreakdown(
            fluency=fluency,
            grammar=grammar,
            vocabulary=vocabulary,
            clarity=clarity,
            structure=structure,
            filler_penalty=penalty,
        ),
    )
