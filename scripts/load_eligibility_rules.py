"""
Run this script to load eligibility rules into Redis.
Usage: python scripts/load_eligibility_rules.py
"""

import json
import sys
import os

# Allow imports from project root regardless of where the script is run from
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from api.redis_client import get_redis
from screening_ai.eligibility_models import EligibilityRules

rules = EligibilityRules(
    job_id="JOB-AUTOMOTIVE_QUALITY_ENGINEER",
    min_ats_score=40.0,
    min_skill_score=25.0,
    min_experience_months=0,
    max_experience_months=600,
    review_band=15.0,
    location_constraints=[],
    availability_required=False,
)

if __name__ == "__main__":
    r = get_redis()
    key = f"eligibility_rules:{rules.job_id}"
    r.set(key, rules.model_dump_json())

    print(f"✓ Eligibility rules loaded into Redis")
    print(f"  Key             : {key}")
    print(f"  job_id          : {rules.job_id}")
    print(f"  min_ats_score   : {rules.min_ats_score}")
    print(f"  min_skill_score : {rules.min_skill_score}")
    print(f"  min_exp_months  : {rules.min_experience_months}")
    print(f"  max_exp_months  : {rules.max_experience_months}")
    print(f"  review_band     : {rules.review_band}")
    print(f"  location_constraints : {rules.location_constraints} (no restriction)")
    print(f"  availability_required: {rules.availability_required}")