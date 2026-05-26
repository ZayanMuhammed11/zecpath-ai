"""
Unit tests for scoring.semantic_scorer.SemanticScorer.

All tests are fully deterministic — no mocking, no LLM calls.
Validates TF-IDF cosine similarity behaviour on realistic QE-domain text.

Run with:
    pytest tests/test_semantic_scorer.py -v
"""

from scoring.semantic_scorer import SemanticScorer


# ─── Shared Text Fixtures ──────────────────────────────────────────────────────

QE_RESUME_TEXT = """
Quality Engineer with 4 years of experience in automotive manufacturing.
Skilled in FMEA, SPC, CAPA, PPAP, APQP, Control Plans, and ISO 9001.
Hands-on experience conducting IATF 16949 internal audits and 8D problem solving.
Implemented Lean Manufacturing and Kaizen initiatives reducing defect rates by 35 percent.
Proficient in root cause analysis using fishbone diagrams and the 5-Why method.
Managed supplier quality using SPC control charts and corrective action workflows.
"""

QE_JD_TEXT = """
We are hiring a Quality Engineer for our automotive Tier-1 manufacturing plant in Pune.
Key requirements: FMEA, SPC, ISO 9001, IATF 16949, CAPA, and internal auditing experience.
Experience with PPAP submissions, APQP planning, and control plan development is mandatory.
Familiarity with Lean Manufacturing, 8D problem solving, and root cause analysis preferred.
Minimum 3 years of hands-on quality assurance experience in an automotive manufacturing role.
"""

COOKING_TEXT = """
Classic French onion soup recipe for a cosy winter dinner.
Caramelise sliced onions in butter over low heat for 45 minutes until deep golden brown.
Add beef broth, a splash of white wine, fresh thyme, and bay leaves.
Simmer for 20 minutes then ladle into oven-safe bowls.
Top each bowl with a toasted baguette slice and grated Gruyere cheese.
Grill under the broiler until the cheese is bubbling and golden.
"""

SHORT_TEXT = "FMEA quality"


# ─── Helper ────────────────────────────────────────────────────────────────────

def make_segmented_resume(
    skills_content: str = "",
    experience_content: str = "",
    other_section: str = "",
    other_content: str = "",
) -> dict:
    """
    Build a minimal Day 8 segmented_resume dict for score_sections() tests.

    Args:
        skills_content: Text for the skills section.
        experience_content: Text for the experience section.
        other_section: Name of an additional non-QE section (e.g. "summary").
        other_content: Text for that additional section.

    Returns:
        Segmented resume dict matching the Day 8 structure.
    """
    sections = []
    if skills_content:
        sections.append({
            "section": "skills",
            "content": skills_content,
            "confidence": 1.0,
            "detection_method": "exact_match",
        })
    if experience_content:
        sections.append({
            "section": "experience",
            "content": experience_content,
            "confidence": 1.0,
            "detection_method": "exact_match",
        })
    if other_section and other_content:
        sections.append({
            "section": other_section,
            "content": other_content,
            "confidence": 1.0,
            "detection_method": "exact_match",
        })
    return {
        "candidate_id": "TEST-SEM-001",
        "sections": sections,
    }


# ─── Tests ─────────────────────────────────────────────────────────────────────

def test_score_qe_resume_vs_qe_jd_returns_valid_range():
    """
    Scoring a realistic QE resume against a QE JD should return a float
    in the range 0.0–100.0.
    """
    scorer = SemanticScorer()
    result = scorer.score(QE_RESUME_TEXT, QE_JD_TEXT)

    assert isinstance(result, float), (
        f"Expected float, got {type(result)}"
    )
    assert 0.0 <= result <= 100.0, (
        f"Expected score in [0.0, 100.0], got {result}"
    )


def test_score_identical_texts_returns_near_perfect():
    """
    Scoring a text against itself should return >= 95.0 because
    cosine similarity of a TF-IDF vector with itself is 1.0.
    """
    scorer = SemanticScorer()
    result = scorer.score(QE_RESUME_TEXT, QE_RESUME_TEXT)

    assert result >= 95.0, (
        f"Expected score >= 95.0 for identical texts, got {result}"
    )


def test_score_unrelated_texts_returns_low_score():
    """
    A cooking recipe scored against a QE engineering JD should return
    under 40.0 due to minimal vocabulary overlap.
    """
    scorer = SemanticScorer()
    result = scorer.score(COOKING_TEXT, QE_JD_TEXT)

    assert result < 40.0, (
        f"Expected score < 40.0 for unrelated texts, got {result}"
    )


def test_score_empty_resume_text_returns_zero():
    """
    An empty resume_text string should return 0.0 without raising any exception.
    """
    scorer = SemanticScorer()
    result = scorer.score("", QE_JD_TEXT)

    assert result == 0.0, (
        f"Expected 0.0 for empty resume_text, got {result}"
    )


def test_score_empty_jd_text_returns_zero():
    """
    An empty jd_text string should return 0.0 without raising any exception.
    """
    scorer = SemanticScorer()
    result = scorer.score(QE_RESUME_TEXT, "")

    assert result == 0.0, (
        f"Expected 0.0 for empty jd_text, got {result}"
    )


def test_score_resume_under_20_chars_returns_zero():
    """
    resume_text under 20 characters after stripping should return 0.0.
    Separately verifies the same guard on jd_text.
    """
    scorer = SemanticScorer()

    result_short_resume = scorer.score(SHORT_TEXT, QE_JD_TEXT)
    assert result_short_resume == 0.0, (
        f"Expected 0.0 for resume under 20 chars, got {result_short_resume}"
    )

    result_short_jd = scorer.score(QE_RESUME_TEXT, SHORT_TEXT)
    assert result_short_jd == 0.0, (
        f"Expected 0.0 for JD under 20 chars, got {result_short_jd}"
    )


def test_score_sections_with_relevant_sections_returns_positive():
    """
    score_sections() should extract skills and experience content and return
    a positive similarity score when matched against a relevant QE JD.
    """
    scorer = SemanticScorer()
    resume = make_segmented_resume(
        skills_content=(
            "FMEA, SPC, CAPA, PPAP, ISO 9001, IATF 16949, "
            "Control Plans, Lean Manufacturing, Kaizen, 8D Problem Solving, "
            "Root Cause Analysis, internal audit, corrective action"
        ),
        experience_content=(
            "Quality Engineer at Tata AutoComp Systems, Pune, 2021 to 2024. "
            "Conducted FMEA reviews and maintained control plans for new launches. "
            "Performed IATF 16949 internal audits and managed CAPA workflows. "
            "Implemented SPC charts for critical-to-quality characteristics."
        ),
    )

    result = scorer.score_sections(resume, QE_JD_TEXT)

    assert isinstance(result, float), (
        f"Expected float, got {type(result)}"
    )
    assert result > 0.0, (
        f"Expected score > 0.0 for matching QE sections vs QE JD, got {result}"
    )


def test_score_sections_no_relevant_sections_returns_zero():
    """
    score_sections() should return 0.0 when the segmented resume contains
    no skills or experience sections — only an irrelevant section like summary.
    """
    scorer = SemanticScorer()
    resume = make_segmented_resume(
        other_section="summary",
        other_content=(
            "Dynamic professional passionate about quality and continuous "
            "improvement in automotive manufacturing environments."
        ),
    )

    result = scorer.score_sections(resume, QE_JD_TEXT)

    assert result == 0.0, (
        f"Expected 0.0 when no skills/experience sections present, got {result}"
    )