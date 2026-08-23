"""
screening_ai/answer_engine.py

Answer intent classification and information-extraction layer.

Sits between the STT cleaning pipeline (Day 24) and the scoring engine
(Day 26).  All functions operate on plain strings and return plain dicts —
no Pydantic models, no Redis, no external calls.
"""

import re
from utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

INTENT_MAP: dict[str, list[str]] = {
    "introduction": ["introduce", "about myself", "background", "my name"],
    "experience": ["experience", "years", "worked", "role", "project", "responsibilities"],
    "skills": ["skills", "technologies", "tools", "stack", "familiar", "proficient"],
    "salary": ["salary", "ctc", "pay", "lpa", "lakhs", "compensation"],
    "availability": ["notice period", "available", "join", "immediate", "serving"],
    "education": ["degree", "studied", "college", "university", "diploma", "b.tech", "b.e"],
    "location": ["location", "city", "based", "relocate", "remote", "working from"],
}

VAGUE_PHRASES: list[str] = [
    "not sure",
    "maybe",
    "i think",
    "probably",
    "i guess",
    "don't know",
    "depends",
]


# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------


def classify_intent(text: str) -> str:
    """Classify the primary intent of an answer using keyword frequency.

    Lowercases *text*, then counts how many keywords from each entry in
    INTENT_MAP appear in the text.  Returns the intent with the highest
    count, or ``"unknown"`` when no keywords match at all.

    Args:
        text: The cleaned answer text to classify.

    Returns:
        One of the INTENT_MAP keys or ``"unknown"``.
    """
    logger.debug("classify_intent called with text=%r", text)
    lower = text.lower()
    scores: dict[str, int] = {
        intent: sum(1 for kw in keywords if kw in lower)
        for intent, keywords in INTENT_MAP.items()
    }
    best_intent = max(scores, key=lambda k: scores[k])
    result = best_intent if scores[best_intent] > 0 else "unknown"
    logger.debug("classify_intent → %r (scores=%s)", result, scores)
    return result


def extract_experience_years(text: str) -> int:
    """Extract a numeric year count from an experience statement.

    Matches patterns like ``"5 years"``, ``"3 yrs"``, ``"10 year"``.

    Args:
        text: The cleaned answer text.

    Returns:
        Integer year count, or ``0`` if no match is found.
    """
    logger.debug("extract_experience_years called")
    match = re.search(r"(\d+)\s*(?:years?|yrs?)", text.lower())
    result = int(match.group(1)) if match else 0
    logger.debug("extract_experience_years → %d", result)
    return result


def extract_salary(text: str) -> str | None:
    """Extract a salary mention from the answer text.

    Matches patterns like ``"8 lpa"``, ``"12 lakhs"``, ``"50k"``,
    ``"15 ctc"``.

    Args:
        text: The cleaned answer text.

    Returns:
        The matched salary string, or ``None`` if no match is found.
    """
    logger.debug("extract_salary called")
    match = re.search(r"(\d+\.?\d*)\s*(?:lpa|lakhs?|k\b|ctc)", text.lower())
    result = match.group(0) if match else None
    logger.debug("extract_salary → %r", result)
    return result


def extract_availability(text: str) -> str:
    """Determine a candidate's availability from their answer.

    Checks for ``"immediate"`` first, then for notice-period indicators
    (``"notice"``, ``"serving"``, ``"days"``, ``"month"``).

    Args:
        text: The cleaned answer text.

    Returns:
        One of ``"Immediate"``, ``"Notice Period"``, or ``"Unknown"``.
    """
    logger.debug("extract_availability called")
    lower = text.lower()
    if "immediate" in lower:
        result = "Immediate"
    elif any(kw in lower for kw in ["notice", "serving", "days", "month"]):
        result = "Notice Period"
    else:
        result = "Unknown"
    logger.debug("extract_availability → %r", result)
    return result


def extract_keywords(text: str, expected_keywords: list[str]) -> list[str]:
    """Return the subset of *expected_keywords* that appear in *text*.

    Matching is case-insensitive via a simple ``in`` membership check on
    the lowercased text.

    Args:
        text: The cleaned answer text.
        expected_keywords: Keywords sourced from the Day 22 question bank.

    Returns:
        List of matched keywords (preserves case of the expected_keywords).
    """
    logger.debug(
        "extract_keywords called with %d expected keywords", len(expected_keywords)
    )
    lower = text.lower()
    result = [kw for kw in expected_keywords if kw.lower() in lower]
    logger.debug("extract_keywords → %r", result)
    return result


def is_vague(text: str) -> bool:
    """Return ``True`` if the answer contains hedging or vague language.

    Checks against VAGUE_PHRASES using a case-insensitive substring match.

    Args:
        text: The cleaned answer text.

    Returns:
        ``True`` if any vague phrase is detected, ``False`` otherwise.
    """
    logger.debug("is_vague called")
    lower = text.lower()
    result = any(phrase in lower for phrase in VAGUE_PHRASES)
    logger.debug("is_vague → %s", result)
    return result


def is_off_topic(intent: str, expected_intent: str | None) -> bool:
    """Determine whether a classified intent matches what was expected.

    When *expected_intent* is ``None``, off-topic is defined as the
    intent being ``"unknown"``.  Otherwise, it is any mismatch between
    *intent* and *expected_intent*.

    Args:
        intent: The intent returned by classify_intent().
        expected_intent: The intent the question was designed to elicit,
            or ``None`` if no expectation was set.

    Returns:
        ``True`` if the answer appears off-topic, ``False`` otherwise.
    """
    logger.debug(
        "is_off_topic called with intent=%r, expected_intent=%r",
        intent,
        expected_intent,
    )
    if expected_intent is None:
        result = intent == "unknown"
    else:
        result = intent != expected_intent
    logger.debug("is_off_topic → %s", result)
    return result


def process_answer(
    question_id: str,
    answer_text: str,
    expected_keywords: list[str] | None = None,
    expected_intent: str | None = None,
) -> dict:
    """Run all extractors on a single answer and return a structured result dict.

    Args:
        question_id: Unique identifier for the question being answered.
        answer_text: The cleaned transcript text from the STT pipeline.
        expected_keywords: Keywords from the Day 22 question bank; treated
            as an empty list when ``None``.
        expected_intent: The intent the question was designed to elicit;
            ``None`` means no intent expectation is set.

    Returns:
        A dict with keys:
            question_id, original_text, intent, keywords_found,
            experience_years, salary, availability, is_vague,
            off_topic, missing_answer.
    """
    logger.debug(
        "process_answer entry — question_id=%s, answer_text=%r", question_id, answer_text
    )

    kw_list: list[str] = expected_keywords if expected_keywords is not None else []

    intent = classify_intent(answer_text)
    keywords_found = extract_keywords(answer_text, kw_list)
    experience_years = extract_experience_years(answer_text)
    salary = extract_salary(answer_text)
    availability = extract_availability(answer_text)
    is_vague_result = is_vague(answer_text)
    off_topic_result = is_off_topic(intent, expected_intent)
    missing_answer = len(answer_text.strip()) < 3

    result = {
        "question_id": question_id,
        "original_text": answer_text,
        "intent": intent,
        "keywords_found": keywords_found,
        "experience_years": experience_years,
        "salary": salary,
        "availability": availability,
        "is_vague": is_vague_result,
        "off_topic": off_topic_result,
        "missing_answer": missing_answer,
    }
    logger.debug("process_answer exit — intent=%r, off_topic=%s", intent, off_topic_result)
    return result


def process_answers_batch(answers: list[dict]) -> list[dict]:
    """Process a list of answer dicts through the full understanding pipeline.

    Each item in *answers* must contain:
        question_id     (str)        — unique question identifier
        answer_text     (str)        — cleaned transcript text
        expected_keywords (list[str]) — optional, defaults to None
        expected_intent   (str)       — optional, defaults to None

    Args:
        answers: List of answer input dicts.

    Returns:
        List of result dicts, one per input, each matching the schema
        returned by process_answer().
    """
    logger.debug("process_answers_batch called with %d answer(s)", len(answers))
    results: list[dict] = []

    for item in answers:
        try:
            result = process_answer(
                question_id=item["question_id"],
                answer_text=item["answer_text"],
                expected_keywords=item.get("expected_keywords"),
                expected_intent=item.get("expected_intent"),
            )
        except Exception as e:
            logger.error(
                "process_answers_batch — error on question_id=%s: %s",
                item.get("question_id"),
                e,
            )
            raise
        results.append(result)

    logger.debug("process_answers_batch complete — %d result(s)", len(results))
    return results
