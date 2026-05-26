"""
JD Parser for Zecpath AI hiring platform.
Extracts structured job profile data from raw JD text using Groq LLM.
"""

import json
import re
from datetime import datetime, timezone

from groq import Groq

import config.settings as settings
from ats_engine.jd_normalizer import JDNormalizer
from ats_engine.synonym_mapper import SynonymMapper
from utils.logger import get_logger
from utils.schemas import JobProfile

logger = get_logger(__name__)

SYSTEM_PROMPT = (
    "You are an expert HR data extraction AI specialized in manufacturing "
    "and industrial quality engineering job descriptions. Extract structured "
    "information from job descriptions and return ONLY valid JSON. "
    "No explanations, no markdown, no code blocks. Return raw JSON only."
)

USER_PROMPT_TEMPLATE = """Extract the following fields from this job description and return as JSON:

{{
  "title": "exact job title from the JD",
  "department": "department name or null",
  "company_name": "company name or null",
  "company_type": "one of: product/service/startup/mnc/government or null",
  "location": "location or null",
  "is_remote": true or false,
  "employment_type": "one of: fulltime/parttime/internship/contract/freelance",
  "experience_required_min_months": integer in months or 0,
  "experience_required_max_months": integer in months or 0,
  "salary_min_inr": integer or null,
  "salary_max_inr": integer or null,
  "required_skills": [
    {{
      "name": "skill name",
      "level": "one of: beginner/intermediate/advanced/expert",
      "years_of_experience": 0.0,
      "is_primary_skill": true
    }}
  ],
  "preferred_skills": [
    {{
      "name": "skill name",
      "level": "beginner/intermediate/advanced/expert",
      "years_of_experience": 0.0,
      "is_primary_skill": false
    }}
  ],
  "must_have_skills": ["skill1", "skill2"],
  "required_education_level": "one of: high_school/diploma/bachelors/masters/phd/any",
  "required_education_field": ["field1", "field2"],
  "responsibilities": ["responsibility1", "responsibility2"],
  "nice_to_have": ["item1", "item2"],
  "scoring_weights": {{
    "skills": 50,
    "experience": 30,
    "education": 10,
    "location": 10
  }}
}}

Rules:
- Experience years mentioned as ranges like 2-5 years: min = 2*12 = 24 months, max = 5*12 = 60 months
- If experience is 0-2 years: min=0, max=24
- Skills mentioned as Required go in required_skills
- Skills mentioned as Preferred or Nice to have go in preferred_skills
- Must have skills are the most critical non-negotiable skills
- Infer skill levels from context:
  basic/knowledge of = beginner
  familiarity/understanding = intermediate
  proficiency/experience in = advanced
  expertise/deep knowledge/advanced = expert
- scoring_weights must always sum to exactly 100
- Return null for fields not mentioned in the JD
- Do not invent information not present in the JD

Job Description:
{jd_text}"""


class JDParser:
    """
    Parses raw job description text into a validated JobProfile dict
    using Groq LLM extraction, synonym mapping, and Pydantic validation.
    """

    def __init__(self):
        """Initialize JDParser with Groq client, normalizer, and synonym mapper."""
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.normalizer = JDNormalizer()
        self.mapper = SynonymMapper()

    def parse(self, jd_text: str, job_id: str) -> dict:
        """
        Full pipeline: normalize JD text, call LLM, map synonyms,
        enrich with metadata, validate with Pydantic, return as dict.

        Args:
            jd_text: Raw job description text.
            job_id: Unique identifier to assign to this job profile.

        Returns:
            Validated JobProfile as a dictionary.

        Raises:
            ValueError: If LLM returns invalid JSON or Pydantic validation fails.
        """
        logger.info(f"JDParser started for job_id: {job_id}")

        # Step 1 — Normalize
        logger.info("Step 1: Normalizing JD text...")
        normalized_text = self.normalizer.normalize(jd_text)
        logger.info(f"Normalized text length: {len(normalized_text)} chars")

        # Step 2 — Call LLM
        logger.info("Step 2: Calling Groq LLM for structured extraction...")
        raw_llm_output = self._call_llm(normalized_text)
        logger.info("LLM call complete.")

        # Step 3 — Parse JSON response
        logger.info("Step 3: Parsing LLM JSON response...")
        parsed_data = self._parse_llm_response(raw_llm_output)
        logger.info("JSON parsed successfully.")

        # Step 4 — Apply synonym mapping
        logger.info("Step 4: Applying synonym mappings...")
        parsed_data["title"] = self.mapper.map_role(parsed_data.get("title", ""))
        parsed_data["required_skills"] = self.mapper.map_skills(
            parsed_data.get("required_skills", [])
        )
        parsed_data["preferred_skills"] = self.mapper.map_skills(
            parsed_data.get("preferred_skills", [])
        )
        logger.info("Synonym mapping complete.")

        # Step 5 — Enrich with system-generated fields
        logger.info("Step 5: Adding system-generated fields...")
        parsed_data["job_id"] = job_id
        parsed_data["job_status"] = "active"
        parsed_data["shortlist_threshold"] = 75.0
        parsed_data["jd_raw_text"] = jd_text
        parsed_data["parsing_metadata"] = {
            "model_used": "groq/llama-3.3-70b-versatile",
            "parsed_at": datetime.now(timezone.utc).isoformat(),
            "confidence_score": 85.0,
            "parsing_version": "v1.0.0",
        }
        logger.info("System fields added.")

        # Step 6 — Validate with Pydantic
        logger.info("Step 6: Validating with JobProfile Pydantic model...")
        validated_model = self._validate(parsed_data)
        logger.info("Pydantic validation passed.")

        # Step 7 — Return as dict
        result = validated_model.model_dump()
        logger.info(f"JDParser complete for job_id: {job_id}")
        return result

    def _call_llm(self, normalized_text: str) -> str:
        """
        Send normalized JD text to Groq LLM and return raw response string.

        Args:
            normalized_text: Clean normalized job description.

        Returns:
            Raw string response from LLM.
        """
        user_prompt = USER_PROMPT_TEMPLATE.format(jd_text=normalized_text)

        response = self.client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            max_tokens=2000,
        )

        return response.choices[0].message.content

    def _parse_llm_response(self, raw_response: str) -> dict:
        """
        Strip markdown fences from LLM output and parse as JSON.

        Args:
            raw_response: Raw string returned by LLM.

        Returns:
            Parsed dict from JSON response.

        Raises:
            ValueError: If JSON cannot be parsed from the response.
        """
        # Strip markdown code fences if present
        cleaned = re.sub(r"```(?:json)?", "", raw_response, flags=re.IGNORECASE)
        cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {e}")
            logger.error(f"Raw LLM output was: {raw_response[:500]}")
            raise ValueError(
                f"LLM returned invalid JSON. Parse error: {e}"
            )

    def _validate(self, data: dict) -> JobProfile:
        """
        Validate the parsed data dict against the JobProfile Pydantic model.

        Args:
            data: Dict of fields to validate.

        Returns:
            Validated JobProfile instance.

        Raises:
            ValueError: If Pydantic validation fails.
        """
        try:
            return JobProfile(**data)
        except Exception as e:
            logger.error(f"Pydantic validation failed: {e}")
            raise ValueError(f"JobProfile validation error: {e}")