"""
RQ task handlers for background resume processing in Zecpath ATS.
These functions run inside the RQ worker process, not the API process.
"""

import json
from datetime import datetime

from ats_engine.experience_parser import ExperienceParser
from ats_engine.skill_extractor import SkillExtractor
from parsers import extract_resume_text, segment_resume
from parsers.education_parser import EducationParser
from parsers.resume_normalizer import normalize_resume_text
from api.redis_client import get_redis
from utils.logger import get_logger

logger = get_logger(__name__)

PARSED_PROFILE_TTL: int = 86400  # 24 hours in seconds


def handle_parse_resume(
    resume_path: str,
    candidate_id: str,
    job_id: str,
    resume_id: str,
) -> dict:
    """
    Full resume parsing pipeline executed as an RQ background task.

    Steps:
        1. Extract raw text from the PDF at resume_path.
        2. Normalise the raw text.
        3. Segment the normalised text into structured sections.
        4. Extract skills using SkillExtractor.
        5. Parse experience using ExperienceParser.
        6. Parse education using EducationParser.
        7. Assemble and store the result in Redis.

    Args:
        resume_path (str): Absolute or relative path to the uploaded PDF file.
        candidate_id (str): Unique identifier for the candidate.
        job_id (str): Job the candidate is being evaluated for.
        resume_id (str): Unique resume identifier generated at upload time.

    Returns:
        dict: The fully parsed candidate profile, also stored in Redis.

    Raises:
        Exception: Re-raises any exception after logging, so RQ marks job failed.
    """
    logger.info(
        "Parse pipeline started — candidate_id=%s, resume_id=%s",
        candidate_id,
        resume_id,
    )

    try:
        # Step 1: Extract raw text from PDF
        raw_text: str = extract_resume_text(resume_path)

        # Step 2: Normalise
        clean_text: str = normalize_resume_text(raw_text)

        # Step 3: Segment into structured sections
        segmented: dict = segment_resume(clean_text, candidate_id)

        # Step 4: Skills extraction
        skill_extractor = SkillExtractor()
        skills: dict = skill_extractor.extract(segmented)

        # Step 5: Experience parsing
        experience_parser = ExperienceParser()
        experience: dict = experience_parser.parse(segmented)

        # Step 6: Education parsing
        education_parser = EducationParser()
        education: dict = education_parser.parse_education(segmented)

        sections_found: list[str] = [k for k, v in segmented.items() if v]
        logger.info(
            "Parse pipeline completed — candidate_id=%s, sections_found=%s",
            candidate_id,
            sections_found,
        )

        result: dict = {
            "candidate_id": candidate_id,
            "job_id": job_id,
            "resume_id": resume_id,
            "resume_path": resume_path,
            "segmented_resume": segmented,
            "skills": skills,
            "experience": experience,
            "education": education,
            "parsed_at": datetime.utcnow().isoformat(),
        }

        redis_conn = get_redis()
        profile_key = f"parsed_profile:{candidate_id}:{resume_id}"
        redis_conn.set(profile_key, json.dumps(result), ex=PARSED_PROFILE_TTL)

        logger.info(
            "Parsed profile stored in Redis — key=%s, ttl=%ds",
            profile_key,
            PARSED_PROFILE_TTL,
        )

        return result

    except Exception as exc:
        logger.error(
            "Parse pipeline ERROR — candidate_id=%s, resume_id=%s: %s",
            candidate_id,
            resume_id,
            exc,
        )
        raise