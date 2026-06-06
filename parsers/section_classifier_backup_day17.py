"""
Section Classifier for Zecpath AI Hiring Platform.
Detects and segments resume sections using rule-based and fuzzy matching.
"""

import re
import difflib
from utils.logger import get_logger

logger = get_logger(__name__)

SECTION_KEYWORDS: dict[str, list[str]] = {
    "summary": [
        "summary", "professional summary",
        "career summary", "profile", "about me",
        "career objective", "objective",
        "professional profile", "overview"
    ],
    "skills": [
        "skills", "technical skills", "skill set",
        "core competencies", "key skills",
        "technologies", "tools", "expertise",
        "technical expertise", "competencies",
        "programming languages", "tech stack"
    ],
    "experience": [
        "experience", "work experience",
        "professional experience", "employment history",
        "work history", "career history",
        "professional background", "employment",
        "internship", "internships",
        "industrial training", "work"
    ],
    "education": [
        "education", "academic background",
        "educational qualification", "qualification",
        "academic history", "academics",
        "educational details", "schooling",
        "university", "college"
    ],
    "certifications": [
        "certifications", "certificates",
        "professional certifications", "licenses",
        "credentials", "accreditations",
        "certified", "certification"
    ],
    "projects": [
        "projects", "project work",
        "personal projects", "academic projects",
        "key projects", "notable projects",
        "portfolio", "project experience"
    ],
    "achievements": [
        "achievements", "accomplishments",
        "awards", "honors", "recognition",
        "awards and honors"
    ],
    "languages": [
        "languages", "language skills",
        "languages known", "spoken languages"
    ],
}

# Flat map: keyword string -> section name (for fast lookup)
_KEYWORD_TO_SECTION: dict[str, str] = {
    kw: section
    for section, keywords in SECTION_KEYWORDS.items()
    for kw in keywords
}

# All known keyword strings (for fuzzy matching pool)
_ALL_KEYWORDS: list[str] = list(_KEYWORD_TO_SECTION.keys())


class SectionClassifier:
    """
    Classifies lines of a cleaned resume text into named sections.

    Uses a two-pass strategy:
      1. Rule-based exact keyword matching (normalized lowercase).
      2. Fuzzy fallback via difflib when no exact match is found.

    Additionally handles ALL-CAPS headings and lines ending with ':'.
    """

    def normalize_line(self, line: str) -> str:
        """
        Normalize a line for keyword comparison.

        Steps:
            - Lowercase
            - Remove all punctuation except spaces
            - Collapse multiple spaces into one
            - Strip leading/trailing whitespace

        Args:
            line: Raw resume line.

        Returns:
            Normalized string.
        """
        lowered = line.lower()
        no_punct = re.sub(r"[^\w\s]", " ", lowered)
        collapsed = re.sub(r"\s+", " ", no_punct)
        return collapsed.strip()

    def _match_section(self, normalized: str) -> tuple[str | None, str]:
        """
        Try to map a normalized line to a section name.

        Returns:
            (section_name, detection_method) or (None, "") if no match.
        """
        # --- Exact match ---
        if normalized in _KEYWORD_TO_SECTION:
            return _KEYWORD_TO_SECTION[normalized], "exact_match"

        # --- Fuzzy fallback ---
        matches = difflib.get_close_matches(
            normalized, _ALL_KEYWORDS, n=1, cutoff=0.7
        )
        if matches:
            return _KEYWORD_TO_SECTION[matches[0]], "fuzzy_match"

        return None, ""

    def is_heading(self, line: str) -> bool:
        """
        Determine whether a line is likely a section heading.

        Criteria (any one is sufficient):
            - Matches SECTION_KEYWORDS exactly or by fuzzy match AND is < 60 chars.
            - Is ALL CAPS and under 50 characters.
            - Ends with ':' and is under 50 characters.

        Args:
            line: Raw resume line.

        Returns:
            True if the line is likely a section heading.
        """
        stripped = line.strip()
        if not stripped:
            return False

        normalized = self.normalize_line(stripped)

        # Rule 1: keyword match (exact or fuzzy) + length guard
        if len(stripped) < 60:
            section, _ = self._match_section(normalized)
            if section:
                return True

        # Rule 2: ALL CAPS heading
        if stripped.isupper() and len(stripped) < 50:
            return True

        # Rule 3: ends with colon
        if stripped.endswith(":") and len(stripped) < 50:
            return True

        return False

    def classify(self, clean_text: str) -> dict[str, list[str]]:
        """
        Split cleaned resume text into named sections.

        Algorithm:
            - Split text into lines.
            - Lines before any heading are grouped under "header".
            - Each recognized heading starts a new section.
            - Lines that belong to no recognized section go to "other".

        Detection priority per heading line:
            1. Exact keyword match   → detection_method = "exact_match"
            2. Fuzzy keyword match   → detection_method = "fuzzy_match"
            3. ALL CAPS rule         → detection_method = "all_caps"
            4. Ends-with-colon rule  → detection_method = "colon_suffix"

        Args:
            clean_text: Cleaned resume text from text_cleaner.py.

        Returns:
            Dict mapping section names to lists of content lines.
            Always contains at least "header" and "other" keys.
        """
        sections: dict[str, list[str]] = {"header": [], "other": []}
        # Track detection method per section for tagger downstream
        self._detection_methods: dict[str, str] = {}

        current_section: str = "header"
        lines = clean_text.splitlines()

        for raw_line in lines:
            stripped = raw_line.strip()

            if not stripped:
                # Preserve blank lines in the current section for readability
                if current_section in sections:
                    sections[current_section].append("")
                continue

            normalized = self.normalize_line(stripped)

            # --- Try section detection ---
            detected_section: str | None = None
            detection_method: str = ""

            if len(stripped) < 60:
                detected_section, detection_method = self._match_section(normalized)

            # ALL CAPS rule (only if keyword match failed)
            if not detected_section and stripped.isupper() and len(stripped) < 50:
                # Attempt one more keyword lookup on the normalized form
                sec, meth = self._match_section(normalized)
                if sec:
                    detected_section, detection_method = sec, meth
                else:
                    # Treat as a generic section using the raw heading text
                    detected_section = normalized
                    detection_method = "all_caps"

            # Ends-with-colon rule
            if not detected_section and stripped.endswith(":") and len(stripped) < 50:
                bare = self.normalize_line(stripped.rstrip(":"))
                sec, meth = self._match_section(bare)
                if sec:
                    detected_section, detection_method = sec, meth
                else:
                    detected_section = bare or normalized.rstrip()
                    detection_method = "colon_suffix"

            if detected_section:
                current_section = detected_section
                if current_section not in sections:
                    sections[current_section] = []
                # Record detection method (first time wins)
                if current_section not in self._detection_methods:
                    self._detection_methods[current_section] = detection_method
                logger.debug(
                    "Section heading detected: '%s' → '%s' (%s)",
                    stripped, current_section, detection_method
                )
            else:
                # Regular content line — append to current section
                if current_section not in sections:
                    sections[current_section] = []
                sections[current_section].append(stripped)

        detected_names = [k for k in sections if k not in ("header", "other")]
        logger.info(
            "classify() complete. Sections detected: %s",
            detected_names
        )
        return sections