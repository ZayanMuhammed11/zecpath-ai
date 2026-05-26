"""
parsers/resume_normalizer.py

Pre-processing step for the Zecpath AI hiring platform.
Standardizes resume section headings and lightly normalizes raw resume text
BEFORE the Day 5 text_cleaner.py pipeline runs.

This module intentionally handles only heading normalization and minimal
character-level cleanup. Full text cleaning (stop-word removal, lemmatization,
tokenization, etc.) is handled exclusively by parsers/text_cleaner.py.
Do NOT duplicate logic from text_cleaner.py here.
"""

import re

from utils.logger import get_logger

logger = get_logger(__name__)


HEADING_SYNONYMS: dict[str, str] = {
    "professional experience": "experience",
    "work experience": "experience",
    "employment history": "experience",
    "professional background": "experience",
    "academic background": "education",
    "educational qualification": "education",
    "academics": "education",
    "technical skills": "skills",
    "skill set": "skills",
    "core competencies": "skills",
    "key skills": "skills",
    "professional certifications": "certifications",
    "certificates": "certifications",
    "career objective": "summary",
    "professional summary": "summary",
    "career profile": "summary",
}


def normalize_headings(text: str) -> str:
    """
    Lowercase the input text and replace known heading synonyms with their
    canonical forms using word-boundary-aware regex substitution.

    Replacement is case-insensitive (text is lowercased first) and avoids
    partial word matches via \\b word boundaries.

    Args:
        text: Raw resume text (may contain mixed-case section headings).

    Returns:
        Text with all recognized heading variants replaced by canonical forms.
    """
    lowered: str = text.lower()
    replacement_count: int = 0

    for synonym, canonical in HEADING_SYNONYMS.items():
        pattern: str = r"\b" + re.escape(synonym) + r"\b"
        new_text, n_subs = re.subn(pattern, canonical, lowered)
        if n_subs:
            replacement_count += n_subs
            lowered = new_text

    logger.debug("normalize_headings — heading replacements made: %d", replacement_count)

    return lowered


def normalize_resume_text(text: str) -> str:
    """
    Pre-process raw resume text for downstream cleaning by text_cleaner.py.

    Steps applied (in order):
        1. normalize_headings()  — canonical section heading substitution.
        2. Strip special characters, retaining: a–z, 0–9, spaces, . , - / ( )
        3. Collapse multiple consecutive spaces into a single space.
        4. Strip leading and trailing whitespace.

    Note:
        This is a pre-processing step only. Full text cleaning — including
        stop-word removal, lemmatization, and tokenization — is handled by
        parsers/text_cleaner.py. Do not add overlapping logic here.

    Args:
        text: Raw resume text string.

    Returns:
        Lightly normalized text ready for the text_cleaner.py pipeline.
    """
    text = normalize_headings(text)
    text = re.sub(r"[^a-z0-9 .,\-/()\n]", " ", text)
    text = re.sub(r" {2,}", " ", text)
    text = text.strip()

    return text