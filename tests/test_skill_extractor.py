"""
Unit tests for ats_engine.skill_extractor.SkillExtractor.

Uses the Day 8 segmented_resume structure where sections is a list of dicts:
    [{"section": "skills", "content": "...", ...}]

Run with:
    pytest tests/test_skill_extractor.py -v
"""

from ats_engine.skill_extractor import SkillExtractor
from utils.schemas import SkillObject


# ─── Helper ────────────────────────────────────────────────────────────────────

def make_resume(skills_content, experience_content="", summary_content=""):
    """
    Build a minimal segmented_resume dict matching the Day 8 structure.
    Only sections with non-empty content are included.
    """
    sections = []

    if skills_content:
        sections.append({
            "section": "skills",
            "content": skills_content,
            "line_count": 1,
            "confidence": 1.0,
            "detection_method": "exact_match",
        })

    if summary_content:
        sections.append({
            "section": "summary",
            "content": summary_content,
            "line_count": 1,
            "confidence": 1.0,
            "detection_method": "exact_match",
        })

    if experience_content:
        sections.append({
            "section": "experience",
            "content": experience_content,
            "line_count": 1,
            "confidence": 1.0,
            "detection_method": "exact_match",
        })

    return {
        "candidate_id": "TEST-001",
        "total_sections_found": len(sections),
        "sections": sections,
        "unclassified_content": "",
        "tagging_metadata": {},
    }


# ─── Tests ─────────────────────────────────────────────────────────────────────

def test_basic_skill_detection():
    """Skills written plainly in the skills section should be detected."""
    extractor = SkillExtractor()
    resume = make_resume(skills_content="Python Django FastAPI")

    results = extractor.extract(resume)
    skill_names = [s["name"] for s in results]

    assert "Python" in skill_names, (
        f"Expected 'Python' in extracted skills, got: {skill_names}"
    )


def test_stack_expansion():
    """The MERN stack keyword should expand to all four component skills."""
    extractor = SkillExtractor()
    resume = make_resume(skills_content="MERN stack developer")

    results = extractor.extract(resume)
    skill_names = [s["name"] for s in results]

    assert "React" in skill_names, (
        f"Expected 'React' (MERN expansion) in: {skill_names}"
    )
    assert "Node" in skill_names, (
        f"Expected 'Node' (MERN expansion) in: {skill_names}"
    )


def test_synonym_normalization():
    """Aliases like ReactJS / NodeJS must resolve to canonical names."""
    extractor = SkillExtractor()
    resume = make_resume(skills_content="ReactJS and NodeJS experience")

    results = extractor.extract(resume)
    skill_names = [s["name"] for s in results]

    assert "React" in skill_names, (
        f"Expected canonical 'React' in: {skill_names}"
    )
    assert "Node" in skill_names, (
        f"Expected canonical 'Node' in: {skill_names}"
    )
    assert "ReactJS" not in skill_names, "'ReactJS' should not appear as a skill name."
    assert "NodeJS" not in skill_names, "'NodeJS' should not appear as a skill name."


def test_deduplication():
    """Multiple mentions of the same skill must yield exactly one result entry."""
    extractor = SkillExtractor()
    resume = make_resume(skills_content="Python Python Python developer")

    results = extractor.extract(resume)
    python_count = sum(1 for s in results if s["name"] == "Python")

    assert python_count == 1, (
        f"Expected 'Python' exactly once in results, found {python_count} times."
    )


def test_confidence_high_frequency():
    """A skill mentioned three or more times should get confidence >= 0.9."""
    extractor = SkillExtractor()
    resume = make_resume(skills_content="Python Python Python developer")

    results = extractor.extract(resume)
    python_result = next((s for s in results if s["name"] == "Python"), None)

    assert python_result is not None, "'Python' not found in results."
    assert python_result["confidence"] >= 0.9, (
        f"Expected confidence >= 0.9 for high-frequency skill, "
        f"got {python_result['confidence']}"
    )


def test_is_primary_skill_flag():
    """A high-confidence skill should have is_primary_skill set to True."""
    extractor = SkillExtractor()
    resume = make_resume(skills_content="Python Python Python")

    results = extractor.extract(resume)
    python_result = next((s for s in results if s["name"] == "Python"), None)

    assert python_result is not None, "'Python' not found in results."
    assert python_result["is_primary_skill"] is True, (
        f"Expected is_primary_skill=True (confidence={python_result['confidence']}), "
        f"got False."
    )


def test_extract_to_skill_objects_returns_pydantic():
    """extract_to_skill_objects() must return validated SkillObject instances."""
    extractor = SkillExtractor()
    resume = make_resume(skills_content="Python Django React")

    result = extractor.extract_to_skill_objects(resume)

    assert len(result) > 0, "Expected at least one SkillObject in results."
    assert isinstance(result[0], SkillObject), (
        f"Expected SkillObject instance, got {type(result[0])}"
    )
    assert result[0].level in ["beginner", "intermediate", "advanced", "expert"], (
        f"Expected a valid SkillLevel string, got '{result[0].level}'"
    )


def test_soft_skill_detection():
    """Soft skills embedded in natural language prose should be detected."""
    extractor = SkillExtractor()
    resume = make_resume(skills_content="Strong communication and leadership skills")

    results = extractor.extract(resume)
    skill_names = [s["name"] for s in results]

    assert "Communication" in skill_names or "Leadership" in skill_names, (
        f"Expected 'Communication' or 'Leadership' in: {skill_names}"
    )