"""
tests/test_fairness_engine.py

Day 15 — Pytest tests for ats_engine/fairness_engine.py.
All tests are deterministic; no mocking is used.
Candidate dicts follow the Day 13 result format used across the Zecpath platform.
"""

import pytest

from ats_engine.fairness_engine import (
    apply_fairness_pipeline,
    evaluate_bias_indicators,
    mask_sensitive_data,
    normalize_scores,
    reduce_keyword_bias,
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def make_candidate(
    candidate_id: str,
    final_score: float,
    skill_score: float,
    semantic_score: float,
    experience_score: float,
    education_score: float,
) -> dict:
    """
    Build a minimal but realistic Day 13-format candidate result dict for
    use in fairness engine tests.

    Args:
        candidate_id:     Unique identifier string.
        final_score:      Overall weighted score (0–100).
        skill_score:      Keyword/skill match sub-score (0–100).
        semantic_score:   Semantic similarity sub-score (0–100).
        experience_score: Experience match sub-score (0–100).
        education_score:  Education match sub-score (0–100).

    Returns:
        A candidate result dict matching the Day 13 output schema.
    """
    return {
        "candidate_id": candidate_id,
        "final_score": final_score,
        "match_label": "Good Match",
        "shortlisted": True,
        "must_haves_met": True,
        "sub_scores": {
            "skills": skill_score,
            "experience": experience_score,
            "education": education_score,
            "certifications": 70.0,
            "semantic": semantic_score,
            "education_combined": education_score,
        },
        "weights_used": {
            "skills": 0.30,
            "experience": 0.25,
            "education": 0.15,
            "certifications": 0.10,
            "semantic": 0.20,
        },
        "shortlist_threshold": 60.0,
        "job_title": "QE Automation Engineer",
        "audit_trail": [],
        # PII fields for masking tests
        "name": "Jane Doe",
        "full_name": "Jane Elizabeth Doe",
        "location": "Bangalore, India",
        "gender": "Female",
        "age": 29,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestNormalizeScores:
    """Tests for normalize_scores()."""

    def test_min_max_normalization_correct(self) -> None:
        """
        Test 1: The candidate with the lowest final_score receives
        normalized_score=0.0 and the highest receives 100.0.
        """
        candidates: list[dict] = [
            make_candidate("C001", final_score=50.0, skill_score=60, semantic_score=55,
                           experience_score=50, education_score=60),
            make_candidate("C002", final_score=70.0, skill_score=75, semantic_score=65,
                           experience_score=70, education_score=70),
            make_candidate("C003", final_score=90.0, skill_score=90, semantic_score=85,
                           experience_score=85, education_score=80),
        ]

        result: list[dict] = normalize_scores(candidates)

        min_candidate = min(result, key=lambda c: c["final_score"])
        max_candidate = max(result, key=lambda c: c["final_score"])

        assert min_candidate["normalized_score"] == 0.0
        assert max_candidate["normalized_score"] == 100.0

    def test_all_equal_scores_returns_100(self) -> None:
        """
        Test 2: When all candidates share the same final_score,
        every normalized_score must be 100.0 (no division by zero).
        """
        candidates: list[dict] = [
            make_candidate("C001", final_score=75.0, skill_score=70, semantic_score=65,
                           experience_score=60, education_score=70),
            make_candidate("C002", final_score=75.0, skill_score=72, semantic_score=68,
                           experience_score=62, education_score=72),
            make_candidate("C003", final_score=75.0, skill_score=74, semantic_score=70,
                           experience_score=64, education_score=74),
        ]

        result: list[dict] = normalize_scores(candidates)

        for candidate in result:
            assert candidate["normalized_score"] == 100.0

    def test_empty_list_returns_empty(self) -> None:
        """
        Test 3: An empty input list must return an empty list immediately.
        """
        result: list[dict] = normalize_scores([])
        assert result == []


class TestMaskSensitiveData:
    """Tests for mask_sensitive_data()."""

    def test_masks_correct_fields_and_sets_flag(self) -> None:
        """
        Test 4: name and full_name are replaced with "MASKED",
        bias_masking_applied is set to True, and location is preserved.
        """
        candidate: dict = make_candidate(
            "C010", final_score=80.0, skill_score=75, semantic_score=70,
            experience_score=65, education_score=80,
        )

        result: dict = mask_sensitive_data(candidate)

        assert result["name"] == "MASKED"
        assert result["full_name"] == "MASKED"
        assert result["gender"] == "MASKED"
        assert result["age"] == "MASKED"
        assert result["bias_masking_applied"] is True
        # Location must NOT be masked
        assert result["location"] == "Bangalore, India"


class TestReduceKeywordBias:
    """Tests for reduce_keyword_bias()."""

    def test_blended_score_calculated_correctly(self) -> None:
        """
        Test 5: skill_score=80, semantic_score=60 with default weights
        (keyword=0.4, semantic=0.6) should return (0.6*60) + (0.4*80) = 68.0.
        """
        result: float = reduce_keyword_bias(skill_score=80.0, semantic_score=60.0)
        assert result == 68.0

    def test_raises_value_error_when_weights_invalid(self) -> None:
        """
        Test 6: Passing weights that do not sum to 1.0 must raise ValueError.
        """
        with pytest.raises(ValueError):
            reduce_keyword_bias(
                skill_score=70.0,
                semantic_score=65.0,
                keyword_weight=0.5,
                semantic_weight=0.6,  # 0.5 + 0.6 = 1.1, invalid
            )


class TestEvaluateBiasIndicators:
    """Tests for evaluate_bias_indicators()."""

    def test_medium_risk_with_two_true_indicators(self) -> None:
        """
        Test 7: A candidate with keyword_dominance=True (skills >> semantic)
        and experience_gap_penalty=True (experience < 40) should receive
        bias_risk_level="medium" (2 True indicators).
        """
        candidate: dict = make_candidate(
            candidate_id="C020",
            final_score=65.0,
            skill_score=85.0,   # skills - semantic = 85 - 50 = 35 > 30 → keyword_dominance
            semantic_score=50.0,
            experience_score=30.0,  # < 40 → experience_gap_penalty
            education_score=70.0,
        )

        report: dict = evaluate_bias_indicators(candidate)

        assert report["bias_indicators"]["keyword_dominance"] is True
        assert report["bias_indicators"]["experience_gap_penalty"] is True
        assert report["bias_risk_level"] == "medium"


class TestApplyFairnessPipeline:
    """Tests for apply_fairness_pipeline()."""

    def test_pipeline_sets_all_required_keys(self) -> None:
        """
        Test 8: After apply_fairness_pipeline(), every candidate dict must
        contain 'fair_score', 'bias_report', and 'normalized_score'.
        """
        candidates: list[dict] = [
            make_candidate("C030", final_score=55.0, skill_score=60, semantic_score=50,
                           experience_score=55, education_score=60),
            make_candidate("C031", final_score=78.0, skill_score=80, semantic_score=70,
                           experience_score=75, education_score=75),
            make_candidate("C032", final_score=91.0, skill_score=92, semantic_score=88,
                           experience_score=90, education_score=85),
        ]

        result: list[dict] = apply_fairness_pipeline(candidates)

        for candidate in result:
            assert "fair_score" in candidate, (
                f"fair_score missing for {candidate['candidate_id']}"
            )
            assert "bias_report" in candidate, (
                f"bias_report missing for {candidate['candidate_id']}"
            )
            assert "normalized_score" in candidate, (
                f"normalized_score missing for {candidate['candidate_id']}"
            )
            assert isinstance(candidate["fair_score"], float)
            assert isinstance(candidate["bias_report"], dict)
            assert isinstance(candidate["normalized_score"], float)