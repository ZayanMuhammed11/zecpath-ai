"""
Unit tests for parsers.education_parser.EducationParser.

All tests use use_llm=False to avoid live API calls.

Run with:
    pytest tests/test_education_parser.py -v
"""

from parsers.education_parser import EducationParser


# ─── Helper ────────────────────────────────────────────────────────────────────

def make_resume(education_content: str = "", cert_content: str = "") -> dict:
    """Build a minimal segmented_resume dict for testing."""
    sections = []
    if education_content:
        sections.append({
            "section": "education",
            "content": education_content,
            "confidence": 1.0,
            "detection_method": "exact_match",
        })
    if cert_content:
        sections.append({
            "section": "certifications",
            "content": cert_content,
            "confidence": 1.0,
            "detection_method": "exact_match",
        })
    return {
        "candidate_id": "TEST-QE-001",
        "sections": sections,
    }


# ─── Sample Texts ──────────────────────────────────────────────────────────────

QE_EDUCATION = """
B.Tech in Mechanical Engineering
XYZ Institute of Technology, Pune
2019 | CGPA: 7.8
"""

FOOD_QE_EDUCATION = """
B.Tech Food Technology
National Institute of Food Technology, Mysore
2020 | 78%
"""

QE_CERTS = """
Six Sigma Green Belt – IASSC Certified, 2022
ISO 9001:2015 Internal Auditor, 2021
Lean Manufacturing Practitioner, 2023
"""

FOOD_QE_CERTS = """
HACCP Certified, 2021
FSSAI Food Safety Supervisor, 2022
ISO 22000 Internal Auditor, 2023
"""


# ─── Tests ─────────────────────────────────────────────────────────────────────

def test_btech_degree_detected():
    """
    Rule-based parser should detect 'B.Tech' from a standard QE education block.
    """
    parser = EducationParser()
    resume = make_resume(education_content=QE_EDUCATION)

    result = parser.parse_education(resume, use_llm=False)

    assert len(result) >= 1, (
        f"Expected at least 1 education entry, got {len(result)}."
    )
    degrees = [e["degree"] for e in result]
    assert any("B.Tech" in d for d in degrees), (
        f"Expected 'B.Tech' in degrees list, got: {degrees}"
    )


def test_education_level_mapped():
    """
    A B.Tech degree should map to education_level == 'bachelors'.
    """
    parser = EducationParser()
    resume = make_resume(education_content=QE_EDUCATION)

    result = parser.parse_education(resume, use_llm=False)

    assert len(result) >= 1, "Expected at least one education entry."
    assert result[0]["education_level"] == "bachelors", (
        f"Expected 'bachelors', got '{result[0]['education_level']}'."
    )


def test_graduation_year_extracted():
    """
    The year 2019 should be extracted as year_of_completion.
    """
    parser = EducationParser()
    resume = make_resume(education_content=QE_EDUCATION)

    result = parser.parse_education(resume, use_llm=False)

    assert len(result) >= 1, "Expected at least one education entry."
    assert result[0]["year_of_completion"] == 2019, (
        f"Expected year_of_completion=2019, got {result[0]['year_of_completion']}."
    )


def test_qe_certification_detected():
    """
    'Six Sigma Green Belt' should be detected from the QE certifications text.
    """
    parser = EducationParser()
    resume = make_resume(cert_content=QE_CERTS)

    result = parser.parse_certifications(resume, use_llm=False)

    cert_names = [c["name"].lower() for c in result]
    assert any("six sigma" in n for n in cert_names), (
        f"Expected a Six Sigma cert in: {cert_names}"
    )


def test_food_safety_certification_detected():
    """
    At least one of HACCP or FSSAI should be detected from food QE cert text.
    """
    parser = EducationParser()
    resume = make_resume(cert_content=FOOD_QE_CERTS)

    result = parser.parse_certifications(resume, use_llm=False)

    cert_names = [c["name"].lower() for c in result]
    assert any("haccp" in n or "fssai" in n for n in cert_names), (
        f"Expected 'haccp' or 'fssai' in cert names, got: {cert_names}"
    )


def test_certification_category_enriched():
    """
    Six Sigma Green Belt should be enriched with category == 'methodology'.
    """
    parser = EducationParser()
    resume = make_resume(cert_content=QE_CERTS)

    result = parser.parse_certifications(resume, use_llm=False)

    six_sigma = next(
        (c for c in result if "six sigma" in c.get("name", "").lower()), None
    )
    assert six_sigma is not None, (
        "Expected a Six Sigma Green Belt entry in results."
    )
    assert "category" in six_sigma, (
        "Expected 'category' key in Six Sigma cert entry."
    )
    assert six_sigma["category"] == "methodology", (
        f"Expected category='methodology', got '{six_sigma['category']}'."
    )


def test_education_relevance_score():
    """
    A B.Tech in Mechanical Engineering should score >= 0.8 against
    required_level='bachelors' and required_fields=['mechanical engineering'].
    """
    from utils.schemas import EducationObject

    parser = EducationParser()
    edu = [
        EducationObject(
            degree="B.Tech",
            field_of_study="Mechanical Engineering",
            institution_name="XYZ Institute",
            location="Pune",
            start_year=2015,
            end_year=2019,
            is_highest_qualification=True,
        )
    ]

    result = parser.calculate_education_relevance(
        edu,
        required_level="bachelors",
        required_fields=["mechanical engineering"],
    )

    assert result["education_relevance_score"] >= 0.8, (
        f"Expected score >= 0.8, got {result['education_relevance_score']}."
    )
    
def test_parse_to_objects_returns_pydantic():
    """
    parse_to_objects() should return a dict with 'education' and
    'certifications' keys containing validated Pydantic instances.
    """
    from utils.schemas import EducationObject, CertificationObject

    parser = EducationParser()
    resume = make_resume(
        education_content=QE_EDUCATION,
        cert_content=QE_CERTS,
    )

    result = parser.parse_to_objects(resume, use_llm=False)

    assert "education" in result, "Expected 'education' key in result dict."
    assert "certifications" in result, "Expected 'certifications' key in result dict."

    assert len(result["education"]) == 1, (
        f"Expected exactly 1 education entry, got {len(result['education'])}."
    )
    assert isinstance(result["education"][0], EducationObject), (
        f"Expected EducationObject, got {type(result['education'][0])}."
    )
    assert result["education"][0].degree == "B.Tech", (
        f"Expected degree='B.Tech', got '{result['education'][0].degree}'."
    )

    assert len(result["certifications"]) == 3, (
        f"Expected exactly 3 certification entries, got {len(result['certifications'])}."
    )
    assert isinstance(result["certifications"][0], CertificationObject), (
        f"Expected CertificationObject, got {type(result['certifications'][0])}."
    )