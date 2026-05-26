"""
Skill Extractor for Zecpath ATS Engine.
Detects, normalises, scores, and levels skills from a segmented resume dict.
"""

import re
from typing import Any

from ats_engine.skill_database import (
    MASTER_SKILL_DB,
    SKILL_LEVEL_INDICATORS,
    SKILL_STACKS,
)
from utils.logger import get_logger
from utils.schemas import SkillLevel, SkillObject

logger = get_logger(__name__)


class SkillExtractor:
    """
    Extracts structured skill information from a segmented resume dictionary.

    The extraction pipeline:
        1. Pull raw text from the resume sections (skills > summary > experience).
        2. Detect canonical skill names via variant/alias matching.
        3. Expand recognised technology stacks into their component skills.
        4. Normalise and deduplicate the skill list.
        5. Score each skill's confidence based on mention frequency and source.
        6. Infer the proficiency level from contextual indicator words.
        7. Return the top-N skills sorted by confidence.
    """

    # ── helpers ────────────────────────────────────────────────────────────────

    @staticmethod
    def _section_text(segmented_resume: dict, key: str) -> str:
        """
        Safely pull text for a named section from segmented_resume["sections"].

        Args:
            segmented_resume: The structured resume dict produced by the segmenter.
            key: Section name, e.g. ``"skills"``, ``"summary"``, ``"experience"``.

        Returns:
            Plain text string for that section, or ``""`` if absent.
        """
        sections = segmented_resume.get("sections", [])
        if isinstance(sections, list):
            for sec in sections:
                if isinstance(sec, dict) and sec.get("section") == key:
                    return sec.get("content", "")
            return ""
        # fallback if sections is a plain dict
        raw = sections.get(key, "")
        return str(raw) if raw else ""

    # ── public API ─────────────────────────────────────────────────────────────

    def extract(
        self,
        segmented_resume: dict,
        top_n: int = 20,
    ) -> list[dict[str, Any]]:
        """
        Main extraction entry-point.

        Args:
            segmented_resume: Dict produced by the resume segmenter, expected to
                contain a ``"sections"`` key mapping section names to text.
            top_n: Maximum number of skills to return (highest confidence first).

        Returns:
            A list of skill dicts, each matching the structure::

                {
                    "name": str,
                    "level": str,
                    "years_of_experience": float,
                    "is_primary_skill": bool,
                    "confidence": float,
                    "category": str,
                    "source": str,
                }
        """
        logger.info("Starting skill extraction (top_n=%d).", top_n)

        # 1. Gather text ────────────────────────────────────────────────────────
        skills_text = self._section_text(segmented_resume, "skills")
        summary_text = self._section_text(segmented_resume, "summary")
        experience_text = self._section_text(segmented_resume, "experience")

        # Use skills section preferentially; fall back to everything combined.
        primary_text = skills_text if skills_text.strip() else (
            skills_text + " " + summary_text + " " + experience_text
        )
        full_text = skills_text + " " + summary_text + " " + experience_text
        full_text_lower = full_text.lower()

        logger.debug(
            "Text lengths — skills: %d, summary: %d, experience: %d.",
            len(skills_text), len(summary_text), len(experience_text),
        )

        # 2. Detect skills in combined text ────────────────────────────────────
        detected = self._detect_skills(full_text)
        logger.info("Raw detected skills (%d): %s", len(detected), detected)

        # 3. Expand stacks ─────────────────────────────────────────────────────
        detected = self._expand_stacks(full_text_lower, detected)
        logger.info("After stack expansion (%d): %s", len(detected), detected)

        # 4. Normalise + deduplicate ───────────────────────────────────────────
        detected = self._normalize_and_deduplicate(detected)
        logger.info("After deduplication (%d): %s", len(detected), detected)

        # 5-7. Score, infer level, build output dicts ──────────────────────────
        results: list[dict[str, Any]] = []
        for skill_name in detected:
            confidence = self._score_confidence(skill_name, skills_text, full_text)
            level = self._infer_level(skill_name, full_text)
            category = MASTER_SKILL_DB.get(skill_name, {}).get("category", "tool")

            # Determine source label
            if skills_text and self._skill_in_text(skill_name, skills_text):
                source = "skills_section"
            elif summary_text and self._skill_in_text(skill_name, summary_text):
                source = "summary_section"
            elif experience_text and self._skill_in_text(skill_name, experience_text):
                source = "experience_section"
            else:
                source = "stack_expansion"

            results.append(
                {
                    "name": skill_name,
                    "level": level,
                    "years_of_experience": 0.0,
                    "is_primary_skill": confidence >= 0.8,
                    "confidence": confidence,
                    "category": category,
                    "source": source,
                }
            )

        # 8. Sort by confidence descending ────────────────────────────────────
        results.sort(key=lambda s: s["confidence"], reverse=True)

        # 9. Return top_n ──────────────────────────────────────────────────────
        top_results = results[:top_n]
        logger.info(
            "Extraction complete. Returning %d skills (of %d detected).",
            len(top_results), len(results),
        )
        return top_results

    def extract_to_skill_objects(
        self,
        segmented_resume: dict,
        top_n: int = 20,
    ) -> list[SkillObject]:
        """
        Convenience wrapper that returns validated Pydantic ``SkillObject`` instances.

        Args:
            segmented_resume: The structured resume dict.
            top_n: Maximum skills to return.

        Returns:
            List of ``SkillObject`` instances.
        """
        raw = self.extract(segmented_resume, top_n=top_n)
        skill_objects: list[SkillObject] = []
        for skill in raw:
            obj = SkillObject(
                name=skill["name"],
                level=SkillLevel(skill["level"]),
                years_of_experience=skill["years_of_experience"],
                is_primary_skill=skill["is_primary_skill"],
            )
            skill_objects.append(obj)

        logger.info(
            "Converted %d skill dicts to SkillObject instances.", len(skill_objects)
        )
        return skill_objects

    # ── internal pipeline steps ────────────────────────────────────────────────

    def _detect_skills(self, text: str) -> list[str]:
        """
        Scan *text* for known skill variants and return canonical skill names.

        Uses ``\\b`` word-boundary matching so that, for example, ``"java"``
        does **not** match inside ``"javascript"``.

        Args:
            text: Raw resume text (any case; lowercased internally).

        Returns:
            List of canonical skill names that were found.
        """
        text_lower = text.lower()
        found: list[str] = []

        for canonical_name, entry in MASTER_SKILL_DB.items():
            for variant in entry["variants"]:
                pattern = r"\b" + re.escape(variant.lower()) + r"\b"
                if re.search(pattern, text_lower):
                    found.append(canonical_name)
                    break  # One variant match is enough per canonical skill

        logger.debug("_detect_skills found: %s", found)
        return found

    def _expand_stacks(self, text_lower: str, detected: list[str]) -> list[str]:
        """
        Expand recognised technology stack keywords into their component skills.

        For example, if ``"mern"`` appears in the text, ``MongoDB``, ``Express``,
        ``React``, and ``Node`` are added to *detected*.

        Args:
            text_lower: Lowercased full resume text.
            detected: Current list of detected canonical skill names.

        Returns:
            Updated list with stack components appended.
        """
        expanded = list(detected)

        for stack_key, components in SKILL_STACKS.items():
            pattern = r"\b" + re.escape(stack_key.lower()) + r"\b"
            if re.search(pattern, text_lower):
                logger.debug("Stack '%s' detected — expanding to %s.", stack_key, components)
                for component in components:
                    if component not in expanded:
                        expanded.append(component)

        return expanded

    def _normalize_and_deduplicate(self, skills: list[str]) -> list[str]:
        """
        Remove duplicate skill names (case-insensitive) while preserving
        the canonical casing from ``MASTER_SKILL_DB``.

        Args:
            skills: Possibly-duplicate list of canonical skill names.

        Returns:
            Deduplicated list retaining first-seen order.
        """
        seen: set[str] = set()
        clean: list[str] = []

        for skill in skills:
            key = skill.lower()
            if key not in seen:
                seen.add(key)
                clean.append(skill)

        logger.debug("_normalize_and_deduplicate: %d → %d skills.", len(skills), len(clean))
        return clean

    def _score_confidence(
        self,
        skill_name: str,
        skills_text: str,
        full_text: str,
    ) -> float:
        """
        Compute a confidence score for a detected skill based on mention frequency
        and the section(s) it appears in.

        Scoring rules:
            * ≥ 3 total occurrences anywhere → **0.95**
            * 2 total occurrences → **0.85**
            * 1 occurrence **inside** the skills section → **0.80**
            * 1 occurrence **outside** the skills section → **0.70**
            * Only found via stack expansion (0 direct occurrences) → **0.75**

        Args:
            skill_name: Canonical skill name.
            skills_text: Raw text of the "skills" section.
            full_text: Combined text of all resume sections.

        Returns:
            Confidence score in the range ``[0.0, 1.0]``.
        """
        entry = MASTER_SKILL_DB.get(skill_name, {})
        variants: list[str] = entry.get("variants", [skill_name.lower()])

        def _count_in(text: str) -> int:
            text_lower = text.lower()
            total = 0
            for variant in variants:
                pattern = r"\b" + re.escape(variant.lower()) + r"\b"
                total += len(re.findall(pattern, text_lower))
            return total

        total_occurrences = _count_in(full_text)
        in_skills_section = _count_in(skills_text)

        if total_occurrences >= 3:
            score = 0.95
        elif total_occurrences == 2:
            score = 0.85
        elif total_occurrences == 1 and in_skills_section >= 1:
            score = 0.80
        elif total_occurrences == 1:
            score = 0.70
        else:
            # Likely a stack-expansion result with no direct mention
            score = 0.75

        logger.debug(
            "_score_confidence('%s'): occurrences=%d, in_skills=%d → %.2f",
            skill_name, total_occurrences, in_skills_section, score,
        )
        return score

    def _infer_level(self, skill_name: str, full_text: str) -> str:
        """
        Infer the proficiency level for a skill by scanning a ±50-character
        window around each mention of the skill in *full_text*.

        Args:
            skill_name: Canonical skill name.
            full_text: Combined resume text.

        Returns:
            One of ``"beginner"``, ``"intermediate"``, ``"advanced"``,
            ``"expert"``.  Defaults to ``"intermediate"`` when no indicator
            words are found.
        """
        entry = MASTER_SKILL_DB.get(skill_name, {})
        variants: list[str] = entry.get("variants", [skill_name.lower()])
        text_lower = full_text.lower()

        WINDOW = 50

        for variant in variants:
            pattern = r"\b" + re.escape(variant.lower()) + r"\b"
            for match in re.finditer(pattern, text_lower):
                start = max(0, match.start() - WINDOW)
                end = min(len(text_lower), match.end() + WINDOW)
                window_text = text_lower[start:end]

                # Check levels from most specific → least specific
                for level in ("expert", "advanced", "intermediate", "beginner"):
                    for indicator in SKILL_LEVEL_INDICATORS[level]:
                        if indicator in window_text:
                            logger.debug(
                                "_infer_level('%s'): matched '%s' → %s",
                                skill_name, indicator, level,
                            )
                            return level

        logger.debug("_infer_level('%s'): no indicator found → intermediate", skill_name)
        return "intermediate"

    # ── private utility ────────────────────────────────────────────────────────

    def _skill_in_text(self, skill_name: str, text: str) -> bool:
        """
        Return ``True`` if *skill_name* (or any of its variants) appears in *text*.

        Args:
            skill_name: Canonical skill name.
            text: Text to search.

        Returns:
            Boolean indicating presence.
        """
        entry = MASTER_SKILL_DB.get(skill_name, {})
        variants: list[str] = entry.get("variants", [skill_name.lower()])
        text_lower = text.lower()

        for variant in variants:
            pattern = r"\b" + re.escape(variant.lower()) + r"\b"
            if re.search(pattern, text_lower):
                return True
        return False