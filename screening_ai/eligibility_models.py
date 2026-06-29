"""
Pydantic v2 models for the Eligibility Decision Engine — Zecpath AI Sprint 2 Day 21.
"""

from datetime import datetime
from typing import Any, List

from pydantic import BaseModel, Field


class EligibilityRules(BaseModel):
    """
    Per-job eligibility rules stored in Redis under eligibility_rules:{job_id}.

    Defaults are permissive so the engine never crashes on missing rules.
    """

    job_id: str
    min_ats_score: float = Field(default=40.0, ge=0, le=100)
    min_skill_score: float = Field(default=25.0, ge=0, le=100)
    min_experience_months: int = Field(default=0, ge=0)
    max_experience_months: int = Field(default=600, ge=0)
    review_band: float = Field(default=15.0, ge=0)  # points below min_ats_score = Review
    location_constraints: List[str] = Field(default_factory=list)  # empty = no restriction
    availability_required: bool = False


class EligibilityCheck(BaseModel):
    """
    Result of a single eligibility rule check.

    Holds the rule name, pass/fail, the candidate's actual value,
    the threshold it was compared against, and an optional note.
    """

    rule: str
    passed: bool
    value: Any        # actual candidate value
    threshold: Any    # rule threshold
    note: str = ""


class EligibilityResult(BaseModel):
    """
    Full eligibility evaluation result for one candidate against one job.

    Stored in Redis under eligibility:{candidate_id}:{job_id}.
    """

    candidate_id: str
    job_id: str
    eligibility_status: str   # "Eligible", "Review", "Rejected"
    final_score: float
    skill_score: float
    experience_months: int
    checks: List[EligibilityCheck]
    evaluated_at: str         # ISO timestamp
    notes: str = ""