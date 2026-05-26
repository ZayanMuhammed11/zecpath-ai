"""
JD Normalizer for Zecpath AI hiring platform.
Cleans and normalizes raw job description text before LLM parsing.
"""

import re
from utils.logger import get_logger

logger = get_logger(__name__)

BOILERPLATE_PHRASES = [
    r"equal opportunity employer",
    r"we are an equal opportunity",
    r"only shortlisted candidates will be contacted",
    r"salary[:\s]+negotiable",
    r"ctc[:\s]+as per industry standards",
]


class JDNormalizer:
    """
    Cleans raw job description text by removing HTML, normalizing bullets,
    stripping boilerplate, and standardizing whitespace.
    """

    def normalize(self, raw_text: str) -> str:
        """
        Apply all cleaning steps in sequence and return normalized text.

        Args:
            raw_text: Raw job description string, possibly with HTML or noise.

        Returns:
            Clean normalized text string.
        """
        char_count_before = len(raw_text)
        logger.info(
            f"JDNormalizer started | Input length: {char_count_before} chars"
        )

        text = self._remove_html_tags(raw_text)
        text = self._normalize_bullets(text)
        text = self._remove_symbol_lines(text)
        text = self._remove_boilerplate(text)
        text = self._normalize_whitespace(text)

        char_count_after = len(text)
        logger.info(
            f"JDNormalizer complete | "
            f"Before: {char_count_before} | "
            f"After: {char_count_after} | "
            f"Reduced by: {char_count_before - char_count_after} chars"
        )

        return text

    def _remove_html_tags(self, text: str) -> str:
        """
        Remove all HTML tags from text.
        Replaces block-level tags with newlines for structure preservation.

        Args:
            text: Input text possibly containing HTML.

        Returns:
            Text with HTML tags stripped.
        """
        # Replace block tags with newlines to preserve structure
        text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"</?p>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"</?li>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"</?div>", "\n", text, flags=re.IGNORECASE)

        # Strip all remaining HTML tags
        text = re.sub(r"<[^>]+>", "", text)

        return text

    def _normalize_bullets(self, text: str) -> str:
        """
        Replace all bullet point variants with standard "- " prefix.

        Args:
            text: Input text with various bullet characters.

        Returns:
            Text with all bullets replaced by "- ".
        """
        bullet_pattern = r"[•●◦‣►▪▸◆]"
        text = re.sub(bullet_pattern, "- ", text)

        # Replace asterisk at start of line with "- "
        text = re.sub(r"^\*\s*", "- ", text, flags=re.MULTILINE)

        return text

    def _remove_symbol_lines(self, text: str) -> str:
        """
        Remove lines that contain only symbols, dashes, or standalone page numbers.

        Args:
            text: Input text.

        Returns:
            Text with symbol-only and page-number-only lines removed.
        """
        cleaned = []
        for line in text.split("\n"):
            stripped = line.strip()

            # Remove lines of only repeated symbols
            if re.fullmatch(r"[-=_*#~|]{2,}", stripped):
                continue

            # Remove standalone page numbers
            if re.fullmatch(r"\d+", stripped):
                continue

            cleaned.append(line)

        return "\n".join(cleaned)

    def _remove_boilerplate(self, text: str) -> str:
        """
        Remove common boilerplate phrases found in job descriptions.

        Args:
            text: Input text.

        Returns:
            Text with boilerplate lines removed.
        """
        for pattern in BOILERPLATE_PHRASES:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)

        return text

    def _normalize_whitespace(self, text: str) -> str:
        """
        Collapse multiple spaces, limit consecutive newlines to 2,
        and strip each line.

        Args:
            text: Input text.

        Returns:
            Text with normalized whitespace.
        """
        # Collapse multiple spaces
        text = re.sub(r" {2,}", " ", text)

        # Strip each line
        lines = [line.strip() for line in text.split("\n")]

        # Limit consecutive blank lines to max 1
        cleaned = []
        blank_count = 0
        for line in lines:
            if line == "":
                blank_count += 1
                if blank_count <= 1:
                    cleaned.append(line)
            else:
                blank_count = 0
                cleaned.append(line)

        return "\n".join(cleaned).strip()