"""
Unit tests for EligibilityEngine — Zecpath AI Sprint 2 Day 21.

All Redis interactions are mocked. No live Redis connection required.
"""

import json
import pytest
from unittest.mock import MagicMock
from screening_ai.eligibility_engine import EligibilityEngine
from screening_ai.eligibility_models import EligibilityRules


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_redis(ats_score_dict=None, profile_dict=None, rules_dict=None):
    """
    Build a mock Redis client that returns controlled data.

    r.get() returns serialised JSON or None based on key prefix.
    r.keys() returns a fake list for parsed_profile pattern.
    """
    r = MagicMock()

    def fake_get(key):
        if key.startswith("ats_score:") and ats_score_dict is not None:
            return json.dumps(ats_score_dict)
        if key.startswith("parsed_profile:") and profile_dict is not None:
            return json.dumps(profile_dict)
        if key.startswith("eligibility_rules:") and rules_dict is not None:
            return json.dumps(rules_dict)
        return None

    def fake_keys(pattern):
        if "parsed_profile:" in pattern and profile_dict is not None:
            candidate_id = pattern.split(":")[1]
            return [f"parsed_profile:{candidate_id}:resume-001"]
        return []

    r.get.side_effect = fake_get
    r.keys.side_effect = fake_keys
    r.set = MagicMock()
    return r


def _ats(score, skill, must_haves_met=True):
    """Build a minimal ats_score dict."""
    return {
        "final_score": score,
        "must_haves_met": must_haves_met,
        "sub_scores": {"skills": skill},
    }


def _profile(exp_months, location="Chennai", is_actively_looking=True):
    """Build a minimal parsed_profile dict."""
    return {
        "total_experience_months": exp_months,
        "location": location,
        "is_actively_looking": is_actively_looking,
    }


# ── Tests ──────────────────────────────────────────────────────────────────────

def test_eligible_candidate():
    """Score=75, skill=40, exp=60m → all checks pass → Eligible."""
    r = _make_redis(ats_score_dict=_ats(75, 40), profile_dict=_profile(60))
    engine = EligibilityEngine(r)
    result = engine.evaluate("C001", "JOB-001")

    assert result is not None
    assert result.eligibility_status == "Eligible"
    assert result.final_score == 75
    assert result.skill_score == 40
    assert result.experience_months == 60


def test_review_candidate():
    """Score=30, skill=30, exp=24m → score in review band (40-15=25) → Review."""
    r = _make_redis(ats_score_dict=_ats(30, 30), profile_dict=_profile(24))
    engine = EligibilityEngine(r)
    result = engine.evaluate("C002", "JOB-001")

    assert result is not None
    assert result.eligibility_status == "Review"


def test_rejected_low_score():
    """Score=10, skill=10, exp=12m → score below review band (40-15=25) → Rejected."""
    r = _make_redis(ats_score_dict=_ats(10, 10), profile_dict=_profile(12))
    engine = EligibilityEngine(r)
    result = engine.evaluate("C003", "JOB-001")

    assert result is not None
    assert result.eligibility_status == "Rejected"


def test_rejected_experience_too_low():
    """exp=0 months, rules require min=12 → experience check fails → Rejected."""
    rules_dict = {
        "job_id": "JOB-001",
        "min_ats_score": 40.0,
        "min_skill_score": 25.0,
        "min_experience_months": 12,
        "max_experience_months": 600,
        "review_band": 15.0,
        "location_constraints": [],
        "availability_required": False,
    }
    r = _make_redis(
        ats_score_dict=_ats(80, 50),
        profile_dict=_profile(0),
        rules_dict=rules_dict,
    )
    engine = EligibilityEngine(r)
    result = engine.evaluate("C004", "JOB-001")

    assert result is not None
    assert result.eligibility_status == "Rejected"
    exp_check = next(c for c in result.checks if c.rule == "experience_range")
    assert exp_check.passed is False


def test_rejected_experience_too_high():
    """exp=700 months, max=600 → experience check fails → Rejected."""
    rules_dict = {
        "job_id": "JOB-001",
        "min_ats_score": 40.0,
        "min_skill_score": 25.0,
        "min_experience_months": 0,
        "max_experience_months": 600,
        "review_band": 15.0,
        "location_constraints": [],
        "availability_required": False,
    }
    r = _make_redis(
        ats_score_dict=_ats(80, 50),
        profile_dict=_profile(700),
        rules_dict=rules_dict,
    )
    engine = EligibilityEngine(r)
    result = engine.evaluate("C005", "JOB-001")

    assert result is not None
    assert result.eligibility_status == "Rejected"
    exp_check = next(c for c in result.checks if c.rule == "experience_range")
    assert exp_check.passed is False


def test_location_pass_no_constraints():
    """Empty location_constraints → location check always passes."""
    r = _make_redis(ats_score_dict=_ats(75, 40), profile_dict=_profile(60, location="Mumbai"))
    engine = EligibilityEngine(r)
    result = engine.evaluate("C006", "JOB-001")

    assert result is not None
    loc_check = next(c for c in result.checks if c.rule == "location")
    assert loc_check.passed is True
    assert loc_check.note == "No location restriction"


def test_location_fail_wrong_location():
    """constraints=["Chennai"], candidate location="Mumbai" → location check fails → Rejected."""
    rules_dict = {
        "job_id": "JOB-001",
        "min_ats_score": 40.0,
        "min_skill_score": 25.0,
        "min_experience_months": 0,
        "max_experience_months": 600,
        "review_band": 15.0,
        "location_constraints": ["Chennai"],
        "availability_required": False,
    }
    r = _make_redis(
        ats_score_dict=_ats(80, 50),
        profile_dict=_profile(60, location="Mumbai"),
        rules_dict=rules_dict,
    )
    engine = EligibilityEngine(r)
    result = engine.evaluate("C007", "JOB-001")

    assert result is not None
    assert result.eligibility_status == "Rejected"
    loc_check = next(c for c in result.checks if c.rule == "location")
    assert loc_check.passed is False


def test_must_haves_not_met_returns_rejected():
    """must_haves_met=False in ATS result → hard reject before eligibility scoring."""
    ats = {
        "final_score": 80.0,
        "must_haves_met": False,
        "sub_scores": {"skills": 70.0},
    }
    r = _make_redis(ats_score_dict=ats, profile_dict=_profile(60))
    engine = EligibilityEngine(r)
    result = engine.evaluate("C009", "JOB-001")

    assert result is not None
    assert result.eligibility_status == "Rejected"
    must_check = next(c for c in result.checks if c.rule == "must_haves_met")
    assert must_check.passed is False


def test_missing_ats_score_returns_none():
    """No ats_score key in Redis → evaluate() returns None."""
    r = _make_redis(ats_score_dict=None, profile_dict=_profile(60))
    engine = EligibilityEngine(r)
    result = engine.evaluate("C008", "JOB-001")

    assert result is None