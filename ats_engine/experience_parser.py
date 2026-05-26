"""
Experience Parsing and Relevance Engine for Zecpath ATS.
Parses structured work experience from segmented resume dicts,
calculates QE relevance scores, and detects career gaps/overlaps.
"""

import re
import json
import math
from datetime import datetime
from dateutil import parser as dateparser
from typing import Optional

from groq import Groq
import config.settings as settings
from utils.schemas import ExperienceObject, CompanyType, EmploymentType
from utils.logger import get_logger


# ─── QE Domain Constants ───────────────────────────────────────────────────────

QE_ROLE_GROUPS: dict[str, list[str]] = {
    "quality_engineer": [
        "quality engineer", "qa engineer", "qc engineer",
        "supplier quality engineer", "sqe",
        "quality assurance engineer",
        "quality control engineer",
    ],
    "quality_manager": [
        "quality manager", "qa manager", "qc manager",
        "quality assurance manager", "quality head",
    ],
    "process_engineer": [
        "process engineer", "manufacturing engineer",
        "production engineer", "ci engineer",
        "continuous improvement engineer",
    ],
    "audit_engineer": [
        "audit engineer", "internal auditor",
        "quality auditor", "system auditor",
    ],
    "reliability_engineer": [
        "reliability engineer", "validation engineer",
        "verification engineer",
    ],
}

QE_TECHNOLOGIES: list[str] = [
    "fmea", "spc", "capa", "ppap", "apqp",
    "iso 9001", "iatf 16949", "as9100", "gmp",
    "haccp", "six sigma", "lean", "kaizen", "5s",
    "8d", "rca", "vsm", "dmaic", "control plans",
    "msa", "gd&t", "fssai", "audit",
]

MONTH_MAP: dict[str, str] = {
    "jan": "01", "feb": "02", "mar": "03",
    "apr": "04", "may": "05", "jun": "06",
    "jul": "07", "aug": "08", "sep": "09",
    "oct": "10", "nov": "11", "dec": "12",
    "january": "01", "february": "02", "march": "03",
    "april": "04", "june": "06", "july": "07",
    "august": "08", "september": "09", "october": "10",
    "november": "11", "december": "12",
}

# ─── LLM System Prompt ─────────────────────────────────────────────────────────

EXPERIENCE_EXTRACTION_PROMPT = """
You are an expert HR data extraction AI for Quality Engineering resumes.
Extract structured experience data from the given text block.

Return ONLY valid JSON array. No explanations, no markdown, no code blocks.
Raw JSON only.

Each experience entry must have these exact fields:
{
  "company_name": "string",
  "role_title": "string",
  "department": "string or null",
  "company_type": "product|service|startup|mnc|government",
  "location": "string, use 'Not specified' if unknown",
  "employment_type": "fulltime|parttime|internship|contract|freelance",
  "start_date": "YYYY-MM format, use YYYY-01 if month unknown",
  "end_date": "YYYY-MM format or null if current",
  "is_current": true or false,
  "responsibilities": ["list of strings"],
  "technologies_used": ["list of QE tools/skills mentioned"],
  "achievements": ["list of measurable outcomes"]
}

Rules:
- company_type: if automotive/industrial/manufacturing → service or mnc
- employment_type: default to fulltime if not stated
- If end date says Present/Current → end_date null, is_current true
- Extract only what is explicitly stated
- technologies_used: include FMEA, SPC, ISO standards etc.
"""


# ─── ExperienceParser Class ────────────────────────────────────────────────────

class ExperienceParser:
    """
    Parses work experience from a segmented resume dict using either an LLM
    (Groq) or a regex-based rule engine.

    Provides additional utilities for:
    - Duration calculation
    - QE relevance scoring
    - Career gap detection
    - Employment overlap detection
    """

    def __init__(self) -> None:
        """Initialise the Groq client and logger."""
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.logger = get_logger(__name__)

    # ── Public API ─────────────────────────────────────────────────────────────

    def parse(
        self,
        segmented_resume: dict,
        use_llm: bool = True,
    ) -> list[dict]:
        """
        Main entry point. Extract experience entries from a segmented resume.

        Args:
            segmented_resume: Structured resume dict from the Day 8 segmenter.
            use_llm: When True (default), the Groq LLM is the primary parser.
                     When False, only the rule-based parser runs (no API call).

        Returns:
            List of experience entry dicts. Each dict contains at minimum:
            company_name, role_title, start_date, end_date, is_current,
            duration_months, technologies_used, responsibilities, achievements.
        """
        # 1. Pull experience section text
        experience_text = self._extract_section_text(segmented_resume, "experience")
        if not experience_text:
            self.logger.warning(
                "No 'experience' section found in segmented_resume. Returning []."
            )
            return []

        self.logger.info("Experience text extracted (%d chars).", len(experience_text))

        # 2. Always run rule-based parse as baseline
        rule_based_result = self._try_rule_based_parse(experience_text)
        self.logger.info(
            "Rule-based parse found %d entries.", len(rule_based_result)
        )

        # 3. Decide primary source
        if use_llm or len(rule_based_result) < 1:
            self.logger.info("Calling LLM parser.")
            llm_result = self._llm_parse(experience_text)
            entries = llm_result if llm_result else rule_based_result
        else:
            entries = rule_based_result

        # 4. Calculate duration for every entry
        entries = [self._calculate_duration_months(e) for e in entries]

        self.logger.info("parse() returning %d experience entries.", len(entries))
        return entries

    def parse_to_objects(
        self,
        segmented_resume: dict,
        use_llm: bool = True,
    ) -> list[ExperienceObject]:
        """
        Parse experience and return validated Pydantic ExperienceObject instances.

        Args:
            segmented_resume: Structured resume dict from the Day 8 segmenter.
            use_llm: Passed through to parse().

        Returns:
            List of validated ExperienceObject instances. Entries that fail
            Pydantic validation are skipped with a warning log.
        """
        raw_entries = self.parse(segmented_resume, use_llm=use_llm)
        objects: list[ExperienceObject] = []

        for entry in raw_entries:
            try:
                obj = ExperienceObject(**entry)
                objects.append(obj)
            except Exception as exc:
                company = entry.get("company_name", "unknown")
                self.logger.warning(
                    "Validation failed for '%s': %s — skipping.", company, exc
                )

        self.logger.info(
            "parse_to_objects(): %d/%d entries validated successfully.",
            len(objects), len(raw_entries),
        )
        return objects

    # ── Internal Parsing ───────────────────────────────────────────────────────

    def _try_rule_based_parse(self, text: str) -> list[dict]:
        """
        Attempt to extract experience blocks using regex patterns.

        Looks for date ranges to split the text into per-role blocks, then
        extracts company name, role title, dates, and QE technologies from
        each block using heuristic rules.

        Args:
            text: Raw experience section text.

        Returns:
            List of partial experience dicts. Missing fields receive safe
            defaults (service / fulltime / Not specified / empty lists).
        """
        self.logger.debug("Running rule-based experience parser.")

        date_anchor_re = re.compile(
            r"""
            (?:
                # Month-Year range: Jan 2021 - Mar 2024
                (?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\.?\s+\d{4})
                \s*[-–to]+\s*
                (?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\.?\s+\d{4}
                   |present|current)
            |
                # MM/YYYY range: 03/2021 – 01/2024
                \d{1,2}/\d{4}\s*[-–]+\s*(?:\d{1,2}/\d{4}|present|current)
            |
                # YYYY-MM range: 2021-01 - 2024-03
                \d{4}-\d{2}\s*[-–]+\s*(?:\d{4}-\d{2}|present|current)
            |
                # Year-only range: 2021 - 2024 or 2021 - Present
                \b\d{4}\s*[-–]+\s*(?:\d{4}|present|current)\b
            )
            """,
            re.IGNORECASE | re.VERBOSE,
        )

        splits = list(date_anchor_re.finditer(text))
        if not splits:
            self.logger.debug("No date anchors found — rule-based returning [].")
            return []

        # Split text into lines once
        lines = text.splitlines()

        # Find which line number each date anchor falls on
        def char_pos_to_line(pos: int) -> int:
            running = 0
            for i, line in enumerate(lines):
                running += len(line) + 1  # +1 for newline
                if running > pos:
                    return i
            return len(lines) - 1

        blocks: list[tuple[re.Match, str]] = []
        for idx, match in enumerate(splits):
            # Block starts at the line containing this date anchor
            start_line = char_pos_to_line(match.start())
            # Go back up to 3 lines to capture company name above date
            block_start_line = max(0, start_line - 3)
            # Block ends at the line just before the next date anchor
            if idx + 1 < len(splits):
                end_line = char_pos_to_line(splits[idx + 1].start())
                block_end_line = max(0, end_line - 1)
            else:
                block_end_line = len(lines)
            block_text = "\n".join(lines[block_start_line:block_end_line])
            blocks.append((match, block_text))

        entries: list[dict] = []
        for date_match, block in blocks:
            entry = self._parse_single_block(date_match.group(), block)
            if entry:
                entries.append(entry)

        self.logger.debug("Rule-based parser extracted %d blocks.", len(entries))
        return entries

    def _parse_single_block(self, date_str: str, block_text: str) -> dict:
        """
        Extract fields from a single experience block.

        Args:
            date_str: The raw date range string found by the date anchor regex.
            block_text: Surrounding text for this role.

        Returns:
            Partial experience dict.
        """
        start_date, end_date, is_current = self._parse_date_range(date_str)

        # Technologies: scan whole block for QE terms
        block_lower = block_text.lower()
        techs_found: list[str] = [
            tech for tech in QE_TECHNOLOGIES if tech in block_lower
        ]

        # Responsibilities: lines that start with - or bullet
        responsibilities: list[str] = []
        for line in block_text.splitlines():
            stripped = line.strip()
            if stripped.startswith(("-", "•", "*")) and len(stripped) > 3:
                responsibilities.append(stripped.lstrip("-•* ").strip())

        # Role title: first line containing a known role keyword
        role_title = "Quality Engineer"  # safe default
        known_role_words = [
            word
            for group in QE_ROLE_GROUPS.values()
            for word in group
        ]
        for line in block_text.splitlines():
            line_lower = line.lower().strip()
            if any(role in line_lower for role in known_role_words):
                role_title = line.strip()
                break

        # Company name: first non-empty line that is not the role title
        #               and doesn't look like a date or bullet
        company_name = "Unknown Company"
        for line in block_text.splitlines():
            stripped = line.strip()
            if (
                stripped
                and not stripped.startswith(("-", "•", "*"))
                and not re.search(r"\d{4}", stripped[:6])
                and stripped.lower() != role_title.lower()
                and len(stripped) > 3
            ):
                company_name = stripped
                break

        return {
            "company_name": company_name,
            "role_title": role_title,
            "department": None,
            "company_type": "service",
            "location": "Not specified",
            "employment_type": "fulltime",
            "start_date": start_date,
            "end_date": end_date,
            "is_current": is_current,
            "responsibilities": responsibilities,
            "technologies_used": techs_found,
            "achievements": [],
        }

    def _llm_parse(self, experience_text: str) -> list[dict]:
        """
        Use the Groq LLM to extract structured experience data.

        Args:
            experience_text: Raw experience section text.

        Returns:
            List of experience dicts parsed from the LLM JSON response.
            Returns [] on any API or JSON parsing error.
        """
        self.logger.info("Calling Groq LLM for experience extraction.")
        try:
            response = self.client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[
                    {"role": "system", "content": EXPERIENCE_EXTRACTION_PROMPT},
                    {"role": "user", "content": experience_text},
                ],
                temperature=0.1,
                max_tokens=2000,
            )
            raw_content = response.choices[0].message.content
            cleaned = re.sub(
                r"```(?:json)?", "", raw_content, flags=re.IGNORECASE
            ).strip()
            parsed = json.loads(cleaned)
            if not isinstance(parsed, list):
                parsed = [parsed]
            self.logger.info("LLM returned %d experience entries.", len(parsed))
            return parsed
        except Exception as exc:
            self.logger.error("LLM parse failed: %s — falling back to rule-based.", exc)
            return []

    # ── Duration Calculation ───────────────────────────────────────────────────

    def _calculate_duration_months(self, entry: dict) -> dict:
        """
        Compute and inject ``duration_months`` into an experience entry dict.

        Args:
            entry: Experience dict containing ``start_date``, ``end_date``,
                   and ``is_current`` fields.

        Returns:
            The same dict with ``duration_months`` added/updated.
        """
        try:
            start = dateparser.parse(entry.get("start_date", "2000-01"))
            if entry.get("is_current") or not entry.get("end_date"):
                end = datetime.now()
            else:
                end = dateparser.parse(entry["end_date"])

            months = (end.year - start.year) * 12 + (end.month - start.month)
            entry["duration_months"] = max(0, months)
        except Exception as exc:
            self.logger.warning(
                "Could not calculate duration for '%s': %s",
                entry.get("company_name", "?"), exc,
            )
            entry["duration_months"] = 0

        return entry

    # ── Relevance Scoring ──────────────────────────────────────────────────────

    def calculate_relevance_score(
        self,
        experiences: list[dict],
        target_role: str,
    ) -> dict:
        """
        Score how relevant a candidate's experience history is to a target QE role.

        Scoring per experience entry:
            1.0  — exact title match to target_role
            0.8  — same QE role group as target
            0.5  — different QE role group
            0.2  — no QE match at all

        Final score is weighted by duration_months.

        Args:
            experiences: List of experience dicts (output of parse()).
            target_role: The role being hired for, e.g. ``"quality engineer"``.

        Returns:
            Dict with keys: relevance_score, target_role, matched_group,
            total_experience_months, relevant_experience_months.
        """
        target_lower = target_role.lower().strip()

        # Find which group the target belongs to
        matched_group: Optional[str] = None
        for group_name, titles in QE_ROLE_GROUPS.items():
            if any(target_lower == t for t in titles):
                matched_group = group_name
                break

        total_months = 0
        relevant_months = 0
        weighted_sum = 0.0

        for exp in experiences:
            months = exp.get("duration_months", 0)
            role_lower = exp.get("role_title", "").lower().strip()
            total_months += months

            # Determine score for this entry
            if role_lower == target_lower:
                score = 1.0
                relevant_months += months
            elif matched_group and any(
                role_lower == t for t in QE_ROLE_GROUPS[matched_group]
            ):
                score = 0.8
                relevant_months += months
            else:
                # Check other QE groups
                in_any_qe_group = any(
                    role_lower == t
                    for g, titles in QE_ROLE_GROUPS.items()
                    for t in titles
                    if g != matched_group
                )
                score = 0.5 if in_any_qe_group else 0.2

            weighted_sum += score * months

        if total_months == 0:
            relevance_score = 0.0
        else:
            relevance_score = round(weighted_sum / total_months, 2)

        self.logger.info(
            "Relevance score for '%s': %.2f (total months: %d).",
            target_role, relevance_score, total_months,
        )
        return {
            "relevance_score": relevance_score,
            "target_role": target_role,
            "matched_group": matched_group,
            "total_experience_months": total_months,
            "relevant_experience_months": relevant_months,
        }

    # ── Gap & Overlap Detection ────────────────────────────────────────────────

    def detect_gaps(self, experiences: list[dict]) -> list[dict]:
        """
        Identify employment gaps longer than 3 months between consecutive roles.

        Args:
            experiences: List of experience dicts sorted by start_date.

        Returns:
            List of gap dicts: after_company, before_company, gap_months, period.
        """
        if len(experiences) < 2:
            return []

        sorted_exp = sorted(
            experiences,
            key=lambda e: e.get("start_date", "1900-01"),
        )

        gaps: list[dict] = []
        for i in range(len(sorted_exp) - 1):
            current = sorted_exp[i]
            next_exp = sorted_exp[i + 1]

            end_str = current.get("end_date")
            start_str = next_exp.get("start_date")

            if not end_str or not start_str:
                continue

            try:
                end_dt = dateparser.parse(end_str)
                start_dt = dateparser.parse(start_str)
                gap_months = (
                    (start_dt.year - end_dt.year) * 12
                    + (start_dt.month - end_dt.month)
                )
                if gap_months > 3:
                    gaps.append(
                        {
                            "after_company": current.get("company_name", "?"),
                            "before_company": next_exp.get("company_name", "?"),
                            "gap_months": gap_months,
                            "period": f"{end_str} to {start_str}",
                        }
                    )
            except Exception as exc:
                self.logger.warning("Gap detection parse error: %s", exc)

        self.logger.info("detect_gaps() found %d gap(s).", len(gaps))
        return gaps

    def detect_overlaps(self, experiences: list[dict]) -> list[dict]:
        """
        Identify pairs of experiences whose date ranges overlap.

        Args:
            experiences: List of experience dicts.

        Returns:
            List of overlap dicts: company_a, company_b, overlap_months.
        """
        overlaps: list[dict] = []
        n = len(experiences)

        for i in range(n):
            for j in range(i + 1, n):
                a = experiences[i]
                b = experiences[j]

                try:
                    a_start = dateparser.parse(a.get("start_date", "1900-01"))
                    b_start = dateparser.parse(b.get("start_date", "1900-01"))

                    a_end_raw = a.get("end_date")
                    b_end_raw = b.get("end_date")
                    a_end = dateparser.parse(a_end_raw) if a_end_raw else datetime.now()
                    b_end = dateparser.parse(b_end_raw) if b_end_raw else datetime.now()

                    # Overlap exists when: a_start < b_end AND a_end > b_start
                    if a_start < b_end and a_end > b_start:
                        overlap_start = max(a_start, b_start)
                        overlap_end = min(a_end, b_end)
                        overlap_months = (
                            (overlap_end.year - overlap_start.year) * 12
                            + (overlap_end.month - overlap_start.month)
                        )
                        overlaps.append(
                            {
                                "company_a": a.get("company_name", "?"),
                                "company_b": b.get("company_name", "?"),
                                "overlap_months": max(0, overlap_months),
                            }
                        )
                except Exception as exc:
                    self.logger.warning("Overlap detection parse error: %s", exc)

        self.logger.info("detect_overlaps() found %d overlap(s).", len(overlaps))
        return overlaps

    # ── Private Utilities ──────────────────────────────────────────────────────

    def _extract_section_text(
        self, segmented_resume: dict, section_name: str
    ) -> str:
        """
        Pull the content string for a named section from segmented_resume.

        Args:
            segmented_resume: The full structured resume dict.
            section_name: Section key to look for, e.g. ``"experience"``.

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

    def _parse_date_range(
        self, date_str: str
    ) -> tuple[str, Optional[str], bool]:
        """
        Parse a raw date-range string into (start_date, end_date, is_current).

        Handles formats such as:
            "Jan 2021 – Mar 2024"  |  "2021-01 - 2024-03"
            "2021 - Present"       |  "03/2021 – 01/2024"

        Args:
            date_str: Raw date-range text extracted by the anchor regex.

        Returns:
            Tuple of (start_YYYY-MM, end_YYYY-MM or None, is_current bool).
        """
        is_current = bool(
            re.search(r"\b(present|current)\b", date_str, re.IGNORECASE)
        )

        # Normalise separators
        normalised = re.sub(r"\s*–\s*|\s+-\s+|\s+to\s+", "|", date_str, flags=re.IGNORECASE)
        parts = normalised.split("|")

        def _to_yyyymm(raw: str) -> str:
            raw = raw.strip()
            # Already YYYY-MM
            if re.fullmatch(r"\d{4}-\d{2}", raw):
                return raw
            # MM/YYYY
            m = re.fullmatch(r"(\d{1,2})/(\d{4})", raw)
            if m:
                return f"{m.group(2)}-{int(m.group(1)):02d}"
            # Month YYYY
            m = re.match(
                r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\.?\s+(\d{4})",
                raw,
                re.IGNORECASE,
            )
            if m:
                month_num = MONTH_MAP.get(m.group(1).lower()[:3], "01")
                return f"{m.group(2)}-{month_num}"
            # YYYY only
            m = re.fullmatch(r"(\d{4})", raw)
            if m:
                return f"{m.group(1)}-01"
            return "2000-01"

        start_date = _to_yyyymm(parts[0]) if parts else "2000-01"
        end_date: Optional[str] = None

        if len(parts) > 1:
            end_raw = parts[1].strip()
            if re.search(r"\b(present|current)\b", end_raw, re.IGNORECASE):
                end_date = None
            else:
                end_date = _to_yyyymm(end_raw)

        return start_date, end_date, is_current