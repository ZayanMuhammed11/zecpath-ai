"""
Text cleaning module for Zecpath AI hiring platform.
Normalizes raw extracted resume text into clean, structured plain text.
"""

import re
from utils.logger import get_logger

logger = get_logger(__name__)

# Known tech keywords commonly broken by column-based PDF extraction
KNOWN_TECH_WORDS = [
    "Python", "Django", "FastAPI", "PostgreSQL", "JavaScript",
    "TypeScript", "ReactJS", "NodeJS", "MongoDB", "Docker",
    "Kubernetes", "TensorFlow", "PyTorch", "LangChain", "LangGraph"
]


class TextCleaner:
    """
    Cleans raw resume text extracted from PDF or DOCX files.
    Applies a sequence of normalization steps to produce consistent output.
    """

    def clean(self, raw_text: str) -> str:
        """
        Run all cleaning steps in sequence and return final clean text.

        Args:
            raw_text: Raw string extracted from a resume file.

        Returns:
            Clean, normalized text string ready for AI parsing.
        """
        char_count_before = len(raw_text)
        logger.info(f"Starting text cleaning | Input length: {char_count_before} chars")

        text = self._remove_special_characters(raw_text)
        logger.info("Step 1 complete: Special characters removed")

        text = self._normalize_bullet_points(text)
        logger.info("Step 2 complete: Bullet points normalized")

        text = self._normalize_whitespace(text)
        logger.info("Step 3 complete: Whitespace normalized")

        text = self._normalize_section_headings(text)
        logger.info("Step 4 complete: Section headings normalized")

        text = self._fix_broken_words(text)
        logger.info("Step 5 complete: Broken words fixed")

        text = self._remove_noise(text)
        logger.info("Step 6 complete: Noise removed")

        char_count_after = len(text)
        logger.info(
            f"Text cleaning complete | "
            f"Before: {char_count_before} chars | "
            f"After: {char_count_after} chars | "
            f"Reduced by: {char_count_before - char_count_after} chars"
        )

        return text

    def _remove_special_characters(self, text: str) -> str:
        """
        Remove null bytes, page breaks, non-breaking spaces,
        zero-width spaces, and other non-printable characters.
        Preserves standard ASCII, unicode letters, newlines, and tabs.

        Args:
            text: Input text string.

        Returns:
            Text with special characters removed or replaced.
        """
        # Remove null bytes
        text = text.replace("\x00", "")

        # Remove page break characters
        text = text.replace("\x0c", "\n")

        # Replace non-breaking spaces with regular space
        text = text.replace("\xa0", " ")

        # Remove zero-width spaces and joiners
        text = text.replace("\u200b", "")
        text = text.replace("\u200c", "")
        text = text.replace("\u200d", "")

        # Remove non-printable characters except newline (\n) and tab (\t)
        text = re.sub(r"[^\x09\x0a\x20-\x7e\u00a1-\uffff]", "", text)

        return text

    def _normalize_bullet_points(self, text: str) -> str:
        """
        Replace all bullet point variants with a consistent "- " prefix.
        Handles common Unicode bullets and asterisks at line starts.

        Args:
            text: Input text string.

        Returns:
            Text with normalized bullet points.
        """
        bullet_variants = r"[•●◦‣►▪▸◆]"
        text = re.sub(bullet_variants, "- ", text)

        # Replace * at start of a line with "- "
        text = re.sub(r"^\*\s*", "- ", text, flags=re.MULTILINE)

        return text

    def _normalize_whitespace(self, text: str) -> str:
        """
        Standardize all whitespace: collapse spaces, limit newlines,
        strip lines, and remove empty lines beyond one blank line.

        Args:
            text: Input text string.

        Returns:
            Text with normalized whitespace.
        """
        # Replace tabs with a single space
        text = text.replace("\t", " ")

        # Replace multiple spaces with a single space (per line)
        text = re.sub(r" {2,}", " ", text)

        # Strip leading and trailing whitespace from each line
        lines = [line.strip() for line in text.split("\n")]

        # Collapse more than 2 consecutive empty lines into 1
        cleaned_lines = []
        empty_count = 0
        for line in lines:
            if line == "":
                empty_count += 1
                if empty_count <= 1:
                    cleaned_lines.append(line)
            else:
                empty_count = 0
                cleaned_lines.append(line)

        return "\n".join(cleaned_lines).strip()

    def _normalize_section_headings(self, text: str) -> str:
        """
        Convert ALL-CAPS short lines (likely section headings) to Title Case.
        Preserves mixed-case and longer lines untouched.

        Args:
            text: Input text string.

        Returns:
            Text with normalized section headings.
        """
        def convert_heading(match: re.Match) -> str:
            line = match.group(0)
            # Only convert if line is short, all caps, and not just numbers/symbols
            if len(line) < 50 and line.isupper() and re.search(r"[A-Z]", line):
                return line.title()
            return line

        # Apply to every line
        text = re.sub(r"^.+$", convert_heading, text, flags=re.MULTILINE)

        return text

    def _fix_broken_words(self, text: str) -> str:
        """
        Repair words broken by column-based PDF extraction.
        Fixes hyphen-at-end-of-line breaks and space-inserted tech words.

        Args:
            text: Input text string.

        Returns:
            Text with broken words joined correctly.
        """
        # Fix hyphenated line breaks: "develop-\nment" -> "development"
        text = re.sub(r"(\w+)-\n(\w+)", r"\1\2", text)

        # Fix known tech words split by spaces from column extraction
        for word in KNOWN_TECH_WORDS:
            # Build a spaced pattern: "Python" -> "P y t h o n" or "Pyt hon"
            # Match the word with optional single spaces between any characters
            spaced_pattern = r"\s?".join(re.escape(ch) for ch in word)
            text = re.sub(spaced_pattern, word, text, flags=re.IGNORECASE)

        return text

    def _remove_noise(self, text: str) -> str:
        """
        Remove common resume noise: standalone page numbers,
        repeated symbol lines, and standard header/footer boilerplate.

        Args:
            text: Input text string.

        Returns:
            Text with noise lines removed.
        """
        cleaned_lines = []

        for line in text.split("\n"):
            stripped = line.strip()

            # Remove lines containing only a number (page numbers)
            if re.fullmatch(r"\d+", stripped):
                continue

            # Remove "Page X of Y" patterns
            if re.fullmatch(r"[Pp]age\s+\d+\s+of\s+\d+", stripped):
                continue

            # Remove common CV header noise
            noise_phrases = [
                "curriculum vitae", "resume", "confidential", "cv"
            ]
            if stripped.lower() in noise_phrases:
                continue

            # Remove lines of only repeated symbols or dashes
            if re.fullmatch(r"[-=_*#~]{3,}", stripped):
                continue

            # Remove lines with only symbols and no alphanumeric content
            if stripped and not re.search(r"[a-zA-Z0-9]", stripped):
                continue

            cleaned_lines.append(line)

        return "\n".join(cleaned_lines)