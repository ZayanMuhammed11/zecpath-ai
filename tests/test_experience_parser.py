"""
Unit tests for ats_engine.experience_parser.ExperienceParser.

All tests use use_llm=False to avoid live API calls.

Run with:
    pytest tests/test_experience_parser.py -v
"""

from ats_engine.experience_parser import ExperienceParser


# ─── Helper ────────────────────────────────────────────────────────────────────

def make_resume(experience_content: str) -> dict:
    """Build a minimal segmented_resume dict with an experience section."""
    return {
        "candidate_id": "TEST-QE-001",
        "sections": [
            {
                "section": "experience",
                "content": experience_content,
                "confidence": 1.0,
                "detection_method": "exact_match",
            }
        ],
    }


# ─── Shared Sample Text ────────────────────────────────────────────────────────

QE_EXPERIENCE = """
Tata AutoComp Systems (2021-01 - 2024-03)
Quality Engineer
Pune, Maharashtra
- Conducted FMEA and Control Plans for new part launches
- Handled CAPA for customer complaints
- Performed internal audits per IATF 16949
- Implemented SPC charts for critical dimensions
- Led 8D problem solving for supplier issues

Bharat Forge Ltd (2019-06 - 2020-12)
Junior Quality Engineer
Pune, Maharashtra
- Assisted in PPAP submissions
- Maintained ISO 9001 quality records
- Supported Six Sigma projects
"""


# ─── Tests ─────────────────────────────────────────────────────────────────────

def test_experience_section_extracted():
    """
    Rule-based parser should find at least one experience entry
    from a well-structured QE resume block.
    """
    parser = ExperienceParser()
    resume = make_resume(QE_EXPERIENCE)

    result = parser.parse(resume, use_llm=False)

    assert len(result) >= 1, (
        f"Expected at least 1 experience entry, got {len(result)}."
    )


def test_duration_months_calculated():
    """
    The Tata AutoComp entry (Jan 2021 – Mar 2024 = 38 months) should have
    duration_months > 0.
    """
    parser = ExperienceParser()
    resume = make_resume(QE_EXPERIENCE)

    result = parser.parse(resume, use_llm=False)
    tata_entry = next(
        (e for e in result if "tata" in e.get("company_name", "").lower()), None
    )

    assert tata_entry is not None, "Expected an entry for Tata AutoComp Systems."
    assert tata_entry["duration_months"] > 0, (
        f"Expected duration_months > 0, got {tata_entry['duration_months']}."
    )


def test_qe_technologies_detected():
    """
    At least one of fmea / capa / spc / iatf 16949 should appear in
    the technologies_used list for the Tata AutoComp entry.
    """
    parser = ExperienceParser()
    resume = make_resume(QE_EXPERIENCE)

    result = parser.parse(resume, use_llm=False)
    tata_entry = next(
        (e for e in result if "tata" in e.get("company_name", "").lower()), None
    )

    assert tata_entry is not None, "Expected an entry for Tata AutoComp Systems."

    techs = [t.lower() for t in tata_entry.get("technologies_used", [])]
    expected_any = {"fmea", "capa", "spc", "iatf 16949"}

    assert expected_any & set(techs), (
        f"Expected at least one of {expected_any} in technologies_used, got: {techs}"
    )


def test_is_current_false_for_past_role():
    """
    Bharat Forge ended in 2020-12 so is_current must be False.
    """
    parser = ExperienceParser()
    resume = make_resume(QE_EXPERIENCE)

    result = parser.parse(resume, use_llm=False)
    bharat_entry = next(
        (e for e in result if "bharat" in e.get("company_name", "").lower()), None
    )

    assert bharat_entry is not None, "Expected an entry for Bharat Forge Ltd."
    assert bharat_entry["is_current"] is False, (
        f"Expected is_current=False for a past role, got {bharat_entry['is_current']}."
    )


def test_gap_detection():
    """
    A 15-month gap between Company A (ends 2019-06) and Company B
    (starts 2020-09) should be detected.
    """
    parser = ExperienceParser()
    gap_text = """
Company A (2018-01 - 2019-06)
Quality Engineer
Pune

Company B (2020-09 - 2023-01)
Senior Quality Engineer
Mumbai
"""
    resume = make_resume(gap_text)

    result = parser.parse(resume, use_llm=False)
    gaps = parser.detect_gaps(result)

    assert len(gaps) >= 1, (
        f"Expected at least 1 gap, got {len(gaps)}. Parsed entries: {result}"
    )
    assert gaps[0]["gap_months"] > 3, (
        f"Expected gap > 3 months, got {gaps[0]['gap_months']}."
    )


def test_relevance_score_exact_match():
    """
    A candidate with 24 months as 'Quality Engineer' targeting
    'quality engineer' should score >= 0.7.
    """
    parser = ExperienceParser()
    experiences = [
        {
            "role_title": "Quality Engineer",
            "duration_months": 24,
            "is_current": False,
        }
    ]

    result = parser.calculate_relevance_score(experiences, "quality engineer")

    assert result["relevance_score"] >= 0.7, (
        f"Expected relevance_score >= 0.7, got {result['relevance_score']}."
    )


def test_relevance_score_related_role():
    """
    A candidate with 24 months as 'QA Manager' targeting 'quality manager'
    (same role group) should score >= 0.5.
    """
    parser = ExperienceParser()
    experiences = [
        {
            "role_title": "QA Manager",
            "duration_months": 24,
            "is_current": False,
        }
    ]

    result = parser.calculate_relevance_score(experiences, "quality manager")

    assert result["relevance_score"] >= 0.5, (
        f"Expected relevance_score >= 0.5, got {result['relevance_score']}."
    )


def test_parse_to_objects_returns_pydantic():
    """
    parse_to_objects() should return ExperienceObject instances
    with non-negative duration_months.
    """
    from utils.schemas import ExperienceObject

    parser = ExperienceParser()
    resume = make_resume(QE_EXPERIENCE)

    result = parser.parse_to_objects(resume, use_llm=False)

    if len(result) > 0:
        assert isinstance(result[0], ExperienceObject), (
            f"Expected ExperienceObject, got {type(result[0])}."
        )
        assert result[0].duration_months >= 0, (
            f"Expected duration_months >= 0, got {result[0].duration_months}."
        )