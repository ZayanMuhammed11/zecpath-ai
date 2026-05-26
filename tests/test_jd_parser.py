"""
Pytest test suite for Zecpath AI JD Parser pipeline.
Covers normalizer, synonym mapper, parser, and batch processor.
"""

import os
import json
import pytest
import tempfile
from unittest.mock import MagicMock, patch

from utils.logger import get_logger
from ats_engine.jd_normalizer import JDNormalizer
from ats_engine.synonym_mapper import SynonymMapper

logger = get_logger(__name__)


# ============================================================
# JD NORMALIZER TESTS
# ============================================================

def test_jd_normalizer_removes_html():
    """
    Ensure JDNormalizer strips HTML tags like <p> and <br>
    from the raw job description text.
    """
    logger.info("Running: test_jd_normalizer_removes_html")
    raw = "<p>We are hiring a <b>QA Engineer</b>.<br/>Join us today.</p>"
    normalizer = JDNormalizer()
    result = normalizer.normalize(raw)

    assert "<p>" not in result
    assert "<b>" not in result
    assert "<br" not in result
    assert "QA Engineer" in result


def test_jd_normalizer_removes_bullets():
    """
    Ensure JDNormalizer replaces bullet variants •, ●, ►
    with "- " consistently.
    """
    logger.info("Running: test_jd_normalizer_removes_bullets")
    raw = "• Python skills\n● Team player\n► Good communicator"
    normalizer = JDNormalizer()
    result = normalizer.normalize(raw)

    assert "•" not in result
    assert "●" not in result
    assert "►" not in result
    assert result.count("- ") >= 3


def test_jd_normalizer_removes_boilerplate():
    """
    Ensure JDNormalizer removes standard boilerplate phrases
    like 'Equal Opportunity Employer'.
    """
    logger.info("Running: test_jd_normalizer_removes_boilerplate")
    raw = (
        "We need a QA Engineer with 3 years experience.\n"
        "Equal Opportunity Employer\n"
        "Only shortlisted candidates will be contacted."
    )
    normalizer = JDNormalizer()
    result = normalizer.normalize(raw)

    assert "Equal Opportunity Employer" not in result
    assert "Only shortlisted candidates will be contacted" not in result
    assert "QA Engineer" in result


# ============================================================
# SYNONYM MAPPER TESTS
# ============================================================

def test_synonym_mapper_role_mapping():
    """
    Ensure SynonymMapper maps 'QA Engineer' to its
    canonical form 'Quality Assurance Engineer'.
    """
    logger.info("Running: test_synonym_mapper_role_mapping")
    mapper = SynonymMapper()
    result = mapper.map_role("QA Engineer")
    assert result == "Quality Assurance Engineer"


def test_synonym_mapper_skill_mapping():
    """
    Ensure SynonymMapper maps skill abbreviation 'SPC' to
    its canonical name 'Statistical Process Control'.
    """
    logger.info("Running: test_synonym_mapper_skill_mapping")
    mapper = SynonymMapper()
    skills = [
        {
            "name": "SPC",
            "level": "advanced",
            "years_of_experience": 2,
            "is_primary_skill": True
        }
    ]
    result = mapper.map_skills(skills)
    assert result[0]["name"] == "Statistical Process Control"


def test_synonym_mapper_no_match_returns_original():
    """
    Ensure SynonymMapper returns the original string unchanged
    when no mapping entry is found for the role.
    """
    logger.info("Running: test_synonym_mapper_no_match_returns_original")
    mapper = SynonymMapper()
    result = mapper.map_role("Python")
    assert result == "Python"


# ============================================================
# JD PARSER TESTS
# ============================================================

def test_jd_parser_invalid_file_raises_error():
    """
    Ensure JDParser.parse() raises ValueError when the Groq API
    returns invalid JSON that cannot be parsed.
    """
    logger.info("Running: test_jd_parser_invalid_file_raises_error")

    with patch("ats_engine.jd_parser.Groq") as MockGroq:
        # Set up mock to return invalid JSON
        mock_client = MagicMock()
        MockGroq.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices[0].message.content = "THIS IS NOT JSON {{{"
        mock_client.chat.completions.create.return_value = mock_response

        from ats_engine.jd_parser import JDParser
        parser = JDParser()

        with pytest.raises(ValueError):
            parser.parse("Some JD text here", "JOB-TEST-001")


# ============================================================
# BATCH PROCESSOR TESTS
# ============================================================

def test_batch_processor_single_file():
    """
    Ensure BatchProcessor.process_single() reads a JD text file,
    calls the parser, and writes the output JSON to data/jd_parsed/.
    Cleans up temp files after test.
    """
    logger.info("Running: test_batch_processor_single_file")

    sample_jd = "We are looking for a Quality Assurance Engineer with 3-5 years experience."
    sample_output = {
        "job_id": "JOB-SAMPLE_JD",
        "title": "Quality Assurance Engineer",
        "department": None,
        "company_name": None,
        "company_type": None,
        "job_status": "active",
        "location": "Bangalore",
        "is_remote": False,
        "employment_type": "fulltime",
        "experience_required_min_months": 36,
        "experience_required_max_months": 60,
        "salary_min_inr": None,
        "salary_max_inr": None,
        "required_skills": [],
        "preferred_skills": [],
        "must_have_skills": [],
        "required_education_level": "bachelors",
        "required_education_field": [],
        "responsibilities": [],
        "nice_to_have": [],
        "shortlist_threshold": 75.0,
        "scoring_weights": {
            "skills": 50,
            "experience": 30,
            "education": 10,
            "location": 10
        },
        "jd_raw_text": sample_jd,
        "parsing_metadata": {
            "model_used": "groq/llama-3.3-70b-versatile",
            "parsed_at": "2024-05-07T10:00:00+00:00",
            "confidence_score": 85.0,
            "parsing_version": "v1.0.0"
        }
    }

    # Create a temp txt file
    tmp_file = tempfile.NamedTemporaryFile(
        suffix=".txt", delete=False, mode="w", encoding="utf-8"
    )
    tmp_file.write(sample_jd)
    tmp_file.close()

    expected_json_path = os.path.join(
        "data", "jd_parsed",
        os.path.splitext(os.path.basename(tmp_file.name))[0] + ".json"
    )

    try:
        with patch("ats_engine.batch_processor.JDParser") as MockParser:
            mock_instance = MagicMock()
            MockParser.return_value = mock_instance
            mock_instance.parse.return_value = sample_output

            from ats_engine.batch_processor import BatchProcessor
            processor = BatchProcessor()
            result = processor.process_single(tmp_file.name)

        assert os.path.exists(expected_json_path), "Output JSON file should be created"
        assert result["job_id"] == "JOB-SAMPLE_JD"

    finally:
        # Cleanup temp files
        if os.path.exists(tmp_file.name):
            os.remove(tmp_file.name)
        if os.path.exists(expected_json_path):
            os.remove(expected_json_path)