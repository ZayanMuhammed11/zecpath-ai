"""
Pytest tests for the Resume Section Segmentation module.
Project: Zecpath AI Hiring Platform
"""

import pytest
from parsers.section_classifier import SectionClassifier
from parsers.section_tagger import SectionTagger
from parsers import segment_resume


# ── Fixtures ───────────────────────────────────────────────────────────────────

SAMPLE_RESUME = """\
Jane Smith
jane.smith@email.com
+91-9876543210

SKILLS
Python
Django
REST APIs

EXPERIENCE
Software Engineer at Acme Corp 2021-2024
Developed backend services using Python and Django.

EDUCATION
B.Tech Computer Science
XYZ University 2017-2021
"""


# ── Unit tests: SectionClassifier ─────────────────────────────────────────────

class TestSectionClassifier:

    def setup_method(self):
        self.classifier = SectionClassifier()

    def test_exact_keyword_detection(self):
        """SKILLS heading must map to the 'skills' section."""
        text = "SKILLS\nPython\nDjango"
        result = self.classifier.classify(text)
        assert "skills" in result, (
            f"Expected 'skills' in sections, got: {list(result.keys())}"
        )
        assert "Python" in result["skills"]
        assert "Django" in result["skills"]

    def test_fuzzy_keyword_detection(self):
        """
        'PROFESSIONAL BACKGROUND' should fuzzy-match to 'professional background'
        which is a keyword for the 'experience' section.
        """
        text = "PROFESSIONAL BACKGROUND\nWorked at TCS"
        result = self.classifier.classify(text)
        assert "experience" in result, (
            f"Expected 'experience' via fuzzy match, got: {list(result.keys())}"
        )

    def test_all_caps_heading_detection(self):
        """ALL-CAPS EDUCATION heading must produce an 'education' section."""
        text = "EDUCATION\nB.Tech Computer Science"
        result = self.classifier.classify(text)
        assert "education" in result, (
            f"Expected 'education' in sections, got: {list(result.keys())}"
        )

    def test_header_section_captures_contact_info(self):
        """Lines before any heading must land in the 'header' section."""
        text = "John Doe\njohn@gmail.com\n+91-9876543210"
        result = self.classifier.classify(text)
        assert "header" in result, "Expected 'header' key in classified sections"
        header_content = " ".join(result["header"])
        assert "John Doe" in header_content
        assert "john@gmail.com" in header_content

    def test_multiple_sections_detected(self):
        """A full resume must produce skills, experience, and education sections."""
        result = self.classifier.classify(SAMPLE_RESUME)
        for expected_section in ("skills", "experience", "education"):
            assert expected_section in result, (
                f"Expected section '{expected_section}' not found. "
                f"Got: {list(result.keys())}"
            )

    def test_is_heading_returns_true_for_keyword(self):
        """is_heading() must return True for known section headings."""
        assert self.classifier.is_heading("SKILLS") is True
        assert self.classifier.is_heading("Education") is True
        assert self.classifier.is_heading("work experience") is True

    def test_is_heading_returns_false_for_content(self):
        """is_heading() must return False for ordinary resume content lines."""
        assert self.classifier.is_heading(
            "Developed REST APIs using Django and FastAPI"
        ) is False

    def test_normalize_line_removes_punctuation(self):
        """normalize_line() must strip punctuation and collapse whitespace."""
        result = self.classifier.normalize_line("  SKILLS:  ")
        assert result == "skills"

    def test_normalize_line_collapses_spaces(self):
        result = self.classifier.normalize_line("work   experience")
        assert result == "work experience"


# ── Unit tests: SectionTagger ─────────────────────────────────────────────────

class TestSectionTagger:

    def setup_method(self):
        self.tagger = SectionTagger()

    def test_section_tagger_confidence_score(self):
        """
        A section detected by exact keyword match must have confidence == 1.0.
        """
        classified = {
            "header": ["John Doe", "john@email.com"],
            "skills": ["Python", "Django", "FastAPI"],
            "other":  [],
        }
        # Inject detection methods as the pipeline would
        self.tagger._injected_detection_methods = {"skills": "exact_match"}
        result = self.tagger.tag(classified, candidate_id="CAND-TEST")

        skills_entry = next(
            (s for s in result["sections"] if s["section"] == "skills"),
            None
        )
        assert skills_entry is not None, "'skills' not found in tagged sections"
        assert skills_entry["confidence"] == 1.0, (
            f"Expected confidence 1.0, got {skills_entry['confidence']}"
        )
        assert skills_entry["detection_method"] == "exact_match"

    def test_section_tagger_fuzzy_confidence(self):
        """Fuzzy-matched sections must have confidence == 0.8."""
        classified = {"experience": ["Worked at TCS"], "header": [], "other": []}
        self.tagger._injected_detection_methods = {"experience": "fuzzy_match"}
        result = self.tagger.tag(classified, candidate_id="CAND-TEST")

        exp_entry = next(
            (s for s in result["sections"] if s["section"] == "experience"),
            None
        )
        assert exp_entry is not None
        assert exp_entry["confidence"] == 0.8

    def test_header_and_other_not_in_sections_list(self):
        """'header' and 'other' must not appear as tagged sections."""
        classified = {
            "header": ["Jane Doe"],
            "other":  ["Some stray line"],
            "skills": ["Python"],
        }
        self.tagger._injected_detection_methods = {"skills": "exact_match"}
        result = self.tagger.tag(classified, "CAND-X")

        section_names = [s["section"] for s in result["sections"]]
        assert "header" not in section_names
        assert "other" not in section_names


# ── Integration tests: segment_resume() ───────────────────────────────────────

class TestSegmentResume:

    def test_section_tagger_output_structure(self):
        """segment_resume() output must contain all required top-level keys."""
        result = segment_resume(SAMPLE_RESUME, candidate_id="CAND-1001")

        required_keys = {
            "candidate_id",
            "sections",
            "total_sections_found",
            "tagging_metadata",
        }
        for key in required_keys:
            assert key in result, f"Missing key '{key}' in segment_resume() output"

        assert result["candidate_id"] == "CAND-1001"
        assert isinstance(result["sections"], list)
        assert isinstance(result["total_sections_found"], int)

        meta = result["tagging_metadata"]
        for meta_key in (
            "classifier_version", "tagged_at",
            "total_lines_processed", "sections_detected"
        ):
            assert meta_key in meta, (
                f"Missing tagging_metadata key: '{meta_key}'"
            )

    def test_empty_text_returns_empty_sections(self):
        """segment_resume('') must return an empty sections list without errors."""
        result = segment_resume("", candidate_id="CAND-EMPTY")

        assert result["sections"] == [], (
            f"Expected empty sections list, got: {result['sections']}"
        )
        assert result["total_sections_found"] == 0

    def test_candidate_id_propagated(self):
        """candidate_id must be preserved in the output dict."""
        result = segment_resume("SKILLS\nPython", candidate_id="CAND-9999")
        assert result["candidate_id"] == "CAND-9999"

    def test_sections_have_required_fields(self):
        """Every section entry must contain all required fields."""
        result = segment_resume(SAMPLE_RESUME, candidate_id="CAND-1001")
        required_fields = {
            "section", "content", "line_count", "confidence", "detection_method"
        }
        for entry in result["sections"]:
            for field in required_fields:
                assert field in entry, (
                    f"Section '{entry.get('section')}' missing field '{field}'"
                )