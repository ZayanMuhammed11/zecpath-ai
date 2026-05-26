"""
Education and Certification Parsing Engine for Zecpath ATS.
Parses structured education and certification data from segmented resume dicts,
with relevance scoring for QE domain job requirements.
"""

import re
import json
from typing import Optional

from groq import Groq
import config.settings as settings
from utils.schemas import EducationObject, CertificationObject, EducationLevel
from utils.logger import get_logger


# ─── QE Domain Constants ───────────────────────────────────────────────────────

DEGREE_PATTERNS: dict[str, str] = {
    "b.tech": "B.Tech",
    "btech": "B.Tech",
    "b.e": "B.E",
    "be ": "B.E",
    "m.tech": "M.Tech",
    "mtech": "M.Tech",
    "m.e": "M.E",
    "diploma": "Diploma",
    "b.sc": "B.Sc",
    "bsc": "B.Sc",
    "m.sc": "M.Sc",
    "msc": "M.Sc",
    "mba": "MBA",
    "b.pharma": "B.Pharma",
    "b.pharm": "B.Pharma",
    "m.pharma": "M.Pharma",
    "phd": "Ph.D",
    "ph.d": "Ph.D",
    "10th": "High School",
    "12th": "Higher Secondary",
    "sslc": "High School",
    "hsc": "Higher Secondary",
}

EDUCATION_LEVEL_MAP: dict[str, str] = {
    "B.Tech": "bachelors",
    "B.E": "bachelors",
    "B.Sc": "bachelors",
    "B.Pharma": "bachelors",
    "Diploma": "diploma",
    "M.Tech": "masters",
    "M.E": "masters",
    "M.Sc": "masters",
    "M.Pharma": "masters",
    "MBA": "masters",
    "Ph.D": "phd",
    "High School": "high_school",
    "Higher Secondary": "high_school",
}

QE_FIELDS_OF_STUDY: list[str] = [
    # Manufacturing QE
    "mechanical engineering",
    "production engineering",
    "industrial engineering",
    "manufacturing engineering",
    "electrical engineering",
    "chemical engineering",
    "metallurgical engineering",
    "materials science",
    # Food QE
    "food technology",
    "food science",
    "dairy technology",
    "agricultural engineering",
    "biotechnology",
    "microbiology",
    "biochemistry",
    # Pharmaceutical QE
    "pharmacy",
    "pharmaceutical sciences",
    "biomedical engineering",
    # General
    "quality engineering",
    "safety engineering",
    "computer science",
    "information technology",
]

QE_CERTIFICATIONS: dict[str, dict] = {
    # Manufacturing & Automotive QE
    "six sigma green belt": {
        "category": "methodology",
        "issuing_body": "ASQ / IASSC",
    },
    "six sigma black belt": {
        "category": "methodology",
        "issuing_body": "ASQ / IASSC",
    },
    "six sigma yellow belt": {
        "category": "methodology",
        "issuing_body": "ASQ / IASSC",
    },
    "lean six sigma": {
        "category": "methodology",
        "issuing_body": "ASQ / IASSC",
    },
    "asq cqe": {
        "category": "quality_standard",
        "issuing_body": "ASQ",
    },
    "certified quality engineer": {
        "category": "quality_standard",
        "issuing_body": "ASQ",
    },
    "asq cqm": {
        "category": "quality_standard",
        "issuing_body": "ASQ",
    },
    "asq cqa": {
        "category": "quality_standard",
        "issuing_body": "ASQ",
    },
    "iso 9001 lead auditor": {
        "category": "quality_standard",
        "issuing_body": "Bureau Veritas / DNV",
    },
    "iso 9001 internal auditor": {
        "category": "quality_standard",
        "issuing_body": "Bureau Veritas / DNV",
    },
    "iatf 16949": {
        "category": "quality_standard",
        "issuing_body": "IATF",
    },
    "lean practitioner": {
        "category": "methodology",
        "issuing_body": "Various",
    },
    "lean manufacturing": {
        "category": "methodology",
        "issuing_body": "Various",
    },
    "fmea practitioner": {
        "category": "methodology",
        "issuing_body": "AIAG",
    },
    "internal auditor": {
        "category": "quality_standard",
        "issuing_body": "Various",
    },
    "as9100": {
        "category": "quality_standard",
        "issuing_body": "SAE International",
    },
    # Food Safety QE
    "haccp": {
        "category": "food_safety",
        "issuing_body": "Codex Alimentarius",
    },
    "fssai": {
        "category": "food_safety",
        "issuing_body": "FSSAI India",
    },
    "iso 22000": {
        "category": "food_safety",
        "issuing_body": "ISO",
    },
    "fssc 22000": {
        "category": "food_safety",
        "issuing_body": "FSSC",
    },
    "food safety": {
        "category": "food_safety",
        "issuing_body": "Various",
    },
    "brc": {
        "category": "food_safety",
        "issuing_body": "BRCGS",
    },
    "sqf": {
        "category": "food_safety",
        "issuing_body": "SQF Institute",
    },
    "codex alimentarius": {
        "category": "food_safety",
        "issuing_body": "Codex Alimentarius",
    },
    "gmp": {
        "category": "food_safety",
        "issuing_body": "Various",
    },
    # Pharmaceutical QE
    "gxp": {
        "category": "pharmaceutical",
        "issuing_body": "Various",
    },
    "ich": {
        "category": "pharmaceutical",
        "issuing_body": "ICH",
    },
    "gmp pharmaceutical": {
        "category": "pharmaceutical",
        "issuing_body": "WHO / FDA",
    },
}

# ─── LLM Prompts ───────────────────────────────────────────────────────────────

EDUCATION_EXTRACTION_PROMPT = """
You are an expert HR data extraction AI for Quality Engineering resumes.
Extract structured education data from the given text.

Return ONLY a valid JSON array. No explanations, no markdown, no code blocks.
Raw JSON only.

Each education entry must have these exact fields:
{
  "degree": "string — normalized degree name",
  "field_of_study": "string — exact field/branch",
  "institution": "string — full institution name, use 'Not specified' if unknown",
  "education_level": "one of: high_school / diploma / bachelors / masters / phd / any",
  "grade": "string CGPA or percentage or null",
  "year_of_completion": integer year or null
}

Rules:
- Extract all education entries found
- Normalize degree names (B.Tech not btech)
- field_of_study: extract exact branch (e.g. Mechanical Engineering, Food Technology)
- Do not invent data not present in text
"""

CERTIFICATION_EXTRACTION_PROMPT = """
You are an expert HR data extraction AI for Quality Engineering resumes.
Extract structured certification data from the given text.

Return ONLY a valid JSON array. No explanations, no markdown, no code blocks.
Raw JSON only.

Each certification entry must have these exact fields:
{
  "name": "string — full certification name",
  "issuing_body": "string or null",
  "year_obtained": integer year or null,
  "expiry_year": integer year or null,
  "is_valid": true or false
}

Rules:
- Extract all certifications mentioned
- is_valid: true unless explicitly expired
- Do not invent data not present in text
- Include QE certifications: Six Sigma, ISO 9001, IATF 16949, HACCP, FSSAI,
  ISO 22000, ASQ, GMP, Lean etc.
"""

# ─── Education level ordering for relevance scoring ────────────────────────────

LEVEL_ORDER: list[str] = ["any", "high_school", "diploma", "bachelors", "masters", "phd"]


# ─── EducationParser Class ─────────────────────────────────────────────────────

class EducationParser:
    """
    Parses education and certification data from a segmented resume dict.

    Supports both LLM-driven (Groq) and rule-based extraction, with fallback
    logic when the LLM is unavailable or disabled. Provides relevance scoring
    for education and certifications against QE job requirements.
    """

    def __init__(self) -> None:
        """Initialise the Groq client and logger."""
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.logger = get_logger(__name__)

    # ── Public API ─────────────────────────────────────────────────────────────

    def parse_education(
        self,
        segmented_resume: dict,
        use_llm: bool = True,
    ) -> list[dict]:
        """
        Main entry point for education extraction.

        Args:
            segmented_resume: Structured resume dict from the Day 8 segmenter.
            use_llm: When True, Groq LLM is the primary parser. When False,
                     only the rule-based parser runs (no API call).

        Returns:
            List of education entry dicts, each normalized via
            ``_normalize_education_entry``.
        """
        text = self._extract_section_text(segmented_resume, "education")
        if not text:
            self.logger.warning("No 'education' section found. Returning [].")
            return []

        self.logger.info("Education text extracted (%d chars).", len(text))

        rule_based = self._rule_based_education(text)
        self.logger.info("Rule-based education parse found %d entries.", len(rule_based))

        if use_llm or len(rule_based) == 0:
            self.logger.info("Calling LLM for education extraction.")
            llm_result = self._llm_education(text)
            entries = llm_result if llm_result else rule_based
        else:
            entries = rule_based

        normalized = [self._normalize_education_entry(e) for e in entries]
        self.logger.info("parse_education() returning %d entries.", len(normalized))
        return normalized

    def parse_certifications(
        self,
        segmented_resume: dict,
        use_llm: bool = True,
    ) -> list[dict]:
        """
        Main entry point for certification extraction.

        Pulls text from the certifications section and also scans the
        experience and summary sections for inline certification mentions.

        Args:
            segmented_resume: Structured resume dict from the Day 8 segmenter.
            use_llm: When True, Groq LLM is the primary parser. When False,
                     only the rule-based parser runs (no API call).

        Returns:
            List of certification entry dicts, enriched with QE_CERTIFICATIONS
            metadata where a canonical name match is found.
        """
        cert_text = self._extract_section_text(segmented_resume, "certifications")
        experience_text = self._extract_section_text(segmented_resume, "experience")
        summary_text = self._extract_section_text(segmented_resume, "summary")
        combined_text = " ".join(
            t for t in [cert_text, experience_text, summary_text] if t
        )

        if not combined_text.strip():
            self.logger.warning("No certification content found. Returning [].")
            return []

        self.logger.info(
            "Certification combined text length: %d chars.", len(combined_text)
        )

        rule_based = self._rule_based_certifications(combined_text)
        self.logger.info(
            "Rule-based certification parse found %d entries.", len(rule_based)
        )

        if use_llm or len(rule_based) == 0:
            self.logger.info("Calling LLM for certification extraction.")
            llm_result = self._llm_certifications(combined_text)
            entries = llm_result if llm_result else rule_based
        else:
            entries = rule_based

        # Enrich with QE_CERTIFICATIONS metadata
        enriched = [self._enrich_certification(e) for e in entries]
        self.logger.info(
            "parse_certifications() returning %d entries.", len(enriched)
        )
        return enriched

    def parse_to_objects(
        self,
        segmented_resume: dict,
        use_llm: bool = True,
    ) -> dict:
        """
        Parse education and certifications and return validated Pydantic objects.

        Args:
            segmented_resume: Structured resume dict from the Day 8 segmenter.
            use_llm: Passed through to parse_education() and parse_certifications().

        Returns:
            Dict with keys ``"education"`` (list of EducationObject) and
            ``"certifications"`` (list of CertificationObject). Entries that
            fail Pydantic validation are skipped with a warning log.
        """
        edu_dicts = self.parse_education(segmented_resume, use_llm=use_llm)
        cert_dicts = self.parse_certifications(segmented_resume, use_llm=use_llm)

        education_objects: list[EducationObject] = []
        for entry in edu_dicts:
            try:
                obj = EducationObject(
                    degree=entry["degree"],
                    field_of_study=entry["field_of_study"],
                    institution_name=entry.get("institution", "Not specified"),
                    location="Not specified",
                    education_level=EducationLevel(entry["education_level"]),
                    start_year=None,
                    end_year=entry.get("year_of_completion"),
                    is_highest_qualification=False,
                )
                education_objects.append(obj)
            except Exception as exc:
                self.logger.warning(
                    "EducationObject validation failed for '%s': %s — skipping.",
                    entry.get("degree", "?"), exc,
                )

        cert_objects: list[CertificationObject] = []
        for entry in cert_dicts:
            try:
                obj = CertificationObject(
                    name=entry["name"],
                    issuing_body=entry.get("issuing_body"),
                    year_obtained=entry.get("year_obtained"),
                    expiry_year=entry.get("expiry_year"),
                    is_valid=entry.get("is_valid", True),
                )
                cert_objects.append(obj)
            except Exception as exc:
                self.logger.warning(
                    "CertificationObject validation failed for '%s': %s — skipping.",
                    entry.get("name", "?"), exc,
                )

        self.logger.info(
            "parse_to_objects(): %d education, %d certification objects.",
            len(education_objects), len(cert_objects),
        )
        return {"education": education_objects, "certifications": cert_objects}

    # ── Rule-Based Parsers ─────────────────────────────────────────────────────

    def _rule_based_education(self, text: str) -> list[dict]:
        """
        Extract education entries using degree-pattern regex matching.

        Scans the text for known degree abbreviations, then pulls the
        graduation year and field of study from the surrounding context.

        Args:
            text: Raw education section text.

        Returns:
            List of partial education dicts. Institution and grade default to
            ``"Not specified"`` and ``None`` respectively (LLM enriches these).
        """
        text_lower = text.lower()
        lines = text.splitlines()
        found_degrees: set[str] = set()
        entries: list[dict] = []

        for pattern_key, canonical_degree in DEGREE_PATTERNS.items():
            if canonical_degree in found_degrees:
                continue

            regex = re.compile(r"\b" + re.escape(pattern_key) + r"\b", re.IGNORECASE)
            match = regex.search(text_lower)
            if not match:
                continue

            found_degrees.add(canonical_degree)
            education_level = EDUCATION_LEVEL_MAP.get(canonical_degree, "any")

            # Year: search entire text for a 4-digit year
            year_match = re.search(r"\b(20\d{2}|19\d{2})\b", text)
            year = int(year_match.group(1)) if year_match else None

            # Field of study: scan lines near the degree match for a known field
            match_line_idx = _char_to_line_idx(match.start(), lines)
            context_lines = lines[
                max(0, match_line_idx - 2): match_line_idx + 3
            ]
            context_lower = " ".join(context_lines).lower()

            field_found = "Not specified"
            for field in QE_FIELDS_OF_STUDY:
                if field in context_lower:
                    field_found = field.title()
                    break

            entries.append(
                {
                    "degree": canonical_degree,
                    "field_of_study": field_found,
                    "institution": "Not specified",
                    "education_level": education_level,
                    "grade": None,
                    "year_of_completion": year,
                }
            )

        self.logger.debug(
            "_rule_based_education() found %d entries.", len(entries)
        )
        return entries

    def _rule_based_certifications(self, text: str) -> list[dict]:
        """
        Extract certifications by matching known QE_CERTIFICATIONS keys.

        Uses word-boundary regex matching. Extracts a year from an 80-character
        window around each match and checks for the word "expired" to set
        ``is_valid``.

        Args:
            text: Combined text from certifications, experience, and summary
                  sections.

        Returns:
            List of certification dicts. Deduplicated by canonical name.
        """
        text_lower = text.lower()
        found_names: set[str] = set()
        entries: list[dict] = []

        for cert_key, meta in QE_CERTIFICATIONS.items():
            if cert_key in found_names:
                continue

            regex = re.compile(r"\b" + re.escape(cert_key) + r"\b", re.IGNORECASE)
            match = regex.search(text_lower)
            if not match:
                continue

            found_names.add(cert_key)

            # 80-char window around the match for year and expiry check
            window_start = max(0, match.start() - 10)
            window_end = min(len(text_lower), match.end() + 80)
            window = text_lower[window_start:window_end]

            year_match = re.search(r"\b(20\d{2}|19\d{2})\b", window)
            year_obtained = int(year_match.group(1)) if year_match else None
            is_valid = "expired" not in window

            entries.append(
                {
                    "name": cert_key.title(),
                    "issuing_body": meta.get("issuing_body"),
                    "year_obtained": year_obtained,
                    "expiry_year": None,
                    "is_valid": is_valid,
                    "category": meta.get("category"),
                }
            )

        self.logger.debug(
            "_rule_based_certifications() found %d entries.", len(entries)
        )
        return entries

    # ── LLM Parsers ────────────────────────────────────────────────────────────

    def _llm_education(self, text: str) -> list[dict]:
        """
        Use the Groq LLM to extract structured education data.

        Args:
            text: Raw education section text.

        Returns:
            List of education dicts from the LLM JSON response.
            Returns [] on any API or JSON parsing error.
        """
        self.logger.info("Calling Groq LLM for education extraction.")
        try:
            response = self.client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[
                    {"role": "system", "content": EDUCATION_EXTRACTION_PROMPT},
                    {"role": "user", "content": text},
                ],
                temperature=0.1,
                max_tokens=1000,
            )
            raw = response.choices[0].message.content
            cleaned = re.sub(r"```(?:json)?", "", raw, flags=re.IGNORECASE).strip()
            parsed = json.loads(cleaned)
            if not isinstance(parsed, list):
                parsed = [parsed]
            self.logger.info("LLM returned %d education entries.", len(parsed))
            return parsed
        except Exception as exc:
            self.logger.error(
                "LLM education extraction failed: %s — returning [].", exc
            )
            return []

    def _llm_certifications(self, text: str) -> list[dict]:
        """
        Use the Groq LLM to extract structured certification data.

        Args:
            text: Combined certification/experience/summary text.

        Returns:
            List of certification dicts from the LLM JSON response.
            Returns [] on any API or JSON parsing error.
        """
        self.logger.info("Calling Groq LLM for certification extraction.")
        try:
            response = self.client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[
                    {"role": "system", "content": CERTIFICATION_EXTRACTION_PROMPT},
                    {"role": "user", "content": text},
                ],
                temperature=0.1,
                max_tokens=1000,
            )
            raw = response.choices[0].message.content
            cleaned = re.sub(r"```(?:json)?", "", raw, flags=re.IGNORECASE).strip()
            parsed = json.loads(cleaned)
            if not isinstance(parsed, list):
                parsed = [parsed]
            self.logger.info("LLM returned %d certification entries.", len(parsed))
            return parsed
        except Exception as exc:
            self.logger.error(
                "LLM certification extraction failed: %s — returning [].", exc
            )
            return []

    # ── Normalization & Enrichment ─────────────────────────────────────────────

    def _normalize_education_entry(self, entry: dict) -> dict:
        """
        Normalize and clean a raw education dict.

        - Maps degree aliases to canonical names via DEGREE_PATTERNS.
        - Maps canonical degree to education_level via EDUCATION_LEVEL_MAP.
        - Title-cases and strips field_of_study and institution.
        - Safely casts year_of_completion to int.

        Args:
            entry: Raw education dict (from rule-based or LLM parser).

        Returns:
            Cleaned and normalized education dict.
        """
        # Normalize degree
        raw_degree = entry.get("degree", "").strip()
        degree_lower = raw_degree.lower()
        canonical_degree = raw_degree  # default to whatever came in
        for pattern_key, canonical in DEGREE_PATTERNS.items():
            if re.search(r"\b" + re.escape(pattern_key) + r"\b", degree_lower):
                canonical_degree = canonical
                break
        entry["degree"] = canonical_degree

        # Normalize education level
        level_from_map = EDUCATION_LEVEL_MAP.get(canonical_degree)
        if level_from_map:
            entry["education_level"] = level_from_map
        elif entry.get("education_level") not in LEVEL_ORDER:
            entry["education_level"] = "any"

        # field_of_study
        entry["field_of_study"] = (
            entry.get("field_of_study", "Not specified") or "Not specified"
        ).strip().title()

        # institution
        institution = (entry.get("institution") or "").strip()
        entry["institution"] = institution if institution else "Not specified"

        # year_of_completion
        raw_year = entry.get("year_of_completion")
        if raw_year is not None:
            try:
                entry["year_of_completion"] = int(raw_year)
            except (ValueError, TypeError):
                entry["year_of_completion"] = None

        return entry

    def _enrich_certification(self, entry: dict) -> dict:
        """
        Enrich a certification dict with category and issuing_body metadata
        from QE_CERTIFICATIONS, if a canonical name match is found.

        Args:
            entry: Raw certification dict.

        Returns:
            The same dict with ``category`` and/or ``issuing_body`` added
            when a match exists.
        """
        name_lower = entry.get("name", "").lower()
        for cert_key, meta in QE_CERTIFICATIONS.items():
            if cert_key in name_lower or name_lower in cert_key:
                entry.setdefault("category", meta.get("category"))
                if not entry.get("issuing_body"):
                    entry["issuing_body"] = meta.get("issuing_body")
                break
        return entry

    # ── Relevance Scoring ──────────────────────────────────────────────────────

    def calculate_education_relevance(
        self,
        education_objects: list[EducationObject],
        required_level: str,
        required_fields: list[str],
    ) -> dict:
        """
        Score candidate education against job requirements.

        Level scoring:
            Meets or exceeds required level → 1.0
            One level below               → 0.7
            Two levels below              → 0.4
            No recognisable level         → 0.2

        Field scoring:
            Any field_of_study matches required_fields → 1.0
            No field match                             → 0.5

        Final score = (level_score * 0.6) + (field_score * 0.4)

        Args:
            education_objects: List of validated EducationObject instances.
            required_level: Minimum education level string, e.g. ``"bachelors"``.
            required_fields: List of acceptable fields of study (case-insensitive
                             partial match).

        Returns:
            Dict with keys: education_relevance_score, highest_level_found,
            required_level, level_score, field_score, field_matched.
        """
        # Find the highest level present by inferring from degree field
        highest_level = "any"
        for edu in education_objects:
            # Infer level from degree using EDUCATION_LEVEL_MAP
            degree_lower = edu.degree.lower().strip()
            inferred_level = "any"
            for pattern_key, canonical in DEGREE_PATTERNS.items():
                if re.search(
                    r"\b" + re.escape(pattern_key) + r"\b",
                    degree_lower
                ):
                    inferred_level = EDUCATION_LEVEL_MAP.get(
                        canonical, "any"
                    )
                    break
            if LEVEL_ORDER.index(inferred_level) > LEVEL_ORDER.index(highest_level):
                highest_level = inferred_level

        # Level score
        req_idx = LEVEL_ORDER.index(required_level) if required_level in LEVEL_ORDER else 0
        found_idx = LEVEL_ORDER.index(highest_level)
        gap = req_idx - found_idx

        if gap <= 0:
            level_score = 1.0
        elif gap == 1:
            level_score = 0.7
        elif gap == 2:
            level_score = 0.4
        else:
            level_score = 0.2

        # Field score
        required_lower = [f.lower() for f in required_fields]
        field_matched = any(
            any(req in (edu.field_of_study or "").lower() for req in required_lower)
            for edu in education_objects
        )
        field_score = 1.0 if field_matched else 0.5

        final_score = round((level_score * 0.6) + (field_score * 0.4), 2)

        self.logger.info(
            "Education relevance: score=%.2f, level=%s, field_matched=%s.",
            final_score, highest_level, field_matched,
        )
        return {
            "education_relevance_score": final_score,
            "highest_level_found": highest_level,
            "required_level": required_level,
            "level_score": level_score,
            "field_score": field_score,
            "field_matched": field_matched,
        }
    
    def calculate_certification_relevance(
        self,
        cert_dicts: list[dict],
        required_categories: list[str],
    ) -> dict:
        """
        Score how well a candidate's certifications match required QE categories.

        Args:
            cert_dicts: List of certification dicts (output of parse_certifications).
            required_categories: List of category strings to match against, e.g.
                                 ``["methodology", "food_safety"]``.

        Returns:
            Dict with keys: certification_relevance_score, total_certifications,
            relevant_certifications, matched_categories.
        """
        total = len(cert_dicts)
        relevant = 0
        matched_categories: list[str] = []

        for cert in cert_dicts:
            category = cert.get("category")
            if category and category in required_categories:
                relevant += 1
                if category not in matched_categories:
                    matched_categories.append(category)

        score = round(relevant / total, 2) if total > 0 else 0.0

        self.logger.info(
            "Certification relevance: score=%.2f, relevant=%d/%d.",
            score, relevant, total,
        )
        return {
            "certification_relevance_score": score,
            "total_certifications": total,
            "relevant_certifications": relevant,
            "matched_categories": matched_categories,
        }

    # ── Private Utility ────────────────────────────────────────────────────────

    def _extract_section_text(
        self, segmented_resume: dict, section_name: str
    ) -> str:
        """
        Pull the content string for a named section from segmented_resume.

        Args:
            segmented_resume: The full structured resume dict.
            section_name: Section key to look for, e.g. ``"education"``.

        Returns:
            Content string, or ``""`` if the section is not found.
        """
        sections = segmented_resume.get("sections", [])

        if isinstance(sections, list):
            for sec in sections:
                if isinstance(sec, dict) and sec.get("section") == section_name:
                    return sec.get("content", "")
            return ""

        # Fallback: plain dict structure
        raw = sections.get(section_name, "")
        return str(raw) if raw else ""


# ─── Module-level helper ───────────────────────────────────────────────────────

def _char_to_line_idx(char_pos: int, lines: list[str]) -> int:
    """
    Convert a character offset in the original text to a line index.

    Args:
        char_pos: Character offset (0-based).
        lines: List of lines from ``text.splitlines()``.

    Returns:
        0-based line index containing that character position.
    """
    running = 0
    for i, line in enumerate(lines):
        running += len(line) + 1  # +1 for the newline
        if running > char_pos:
            return i
    return max(0, len(lines) - 1)