"""
Eligibility Decision Engine — Zecpath AI Sprint 2 Day 21

Reads ATS score from Redis, applies job-specific eligibility rules,
writes result to Redis under eligibility:{candidate_id}:{job_id}.

All Redis values are plain dicts. Always use .get() with defaults.
Never use dot notation on Redis-sourced data.
"""

import json
from datetime import datetime, timezone
from typing import List, Optional

from screening_ai.eligibility_models import (
    EligibilityCheck,
    EligibilityResult,
    EligibilityRules,
)
from utils.logger import get_logger


class EligibilityEngine:
    """
    Orchestrates eligibility evaluation for candidates against job-specific rules.

    Reads pre-computed ATS scores and parsed profiles from Redis (Sprint 1 keys),
    applies configurable rule checks, determines status, and writes results back
    to Redis under eligibility:{candidate_id}:{job_id}.
    """

    def __init__(self, redis_client) -> None:
        """
        Initialise the engine with a Redis client instance.

        Args:
            redis_client: A connected Redis client (from api.redis_client.get_redis).
        """
        self.r = redis_client
        self.logger = get_logger(__name__)

    def load_rules(self, job_id: str) -> EligibilityRules:
        """
        Load job-specific eligibility rules from Redis.

        Reads eligibility_rules:{job_id}. If the key does not exist,
        returns an EligibilityRules instance with all defaults — the engine
        never crashes on missing rules.

        Args:
            job_id: The job identifier.

        Returns:
            EligibilityRules: Parsed rules or defaults.
        """
        key = f"eligibility_rules:{job_id}"
        raw = self.r.get(key)
        if raw is None:
            self.logger.warning(
                "No eligibility rules found for job_id=%s — using defaults", job_id
            )
            return EligibilityRules(job_id=job_id)

        rules_dict: dict = json.loads(raw)
        return EligibilityRules(**rules_dict)

    def load_ats_score(self, candidate_id: str, job_id: str) -> Optional[dict]:
        """
        Load the ATS score dict from Redis for a candidate/job pair.

        Reads ats_score:{candidate_id}:{job_id}.

        Args:
            candidate_id: The candidate identifier.
            job_id: The job identifier.

        Returns:
            Parsed dict or None if key not found.
        """
        key = f"ats_score:{candidate_id}:{job_id}"
        raw = self.r.get(key)
        if raw is None:
            self.logger.warning(
                "ATS score not found — candidate_id=%s, job_id=%s", candidate_id, job_id
            )
            return None
        return json.loads(raw)

    def load_parsed_profile(self, candidate_id: str) -> Optional[dict]:
        """
        Load the parsed candidate profile from Redis.

        Uses r.keys() to find any matching parsed_profile:{candidate_id}:* key,
        since the resume_id suffix is not known at this stage.

        Args:
            candidate_id: The candidate identifier.

        Returns:
            Parsed profile dict or None if no matching key found.
        """
        pattern = f"parsed_profile:{candidate_id}:*"
        matching_keys = self.r.keys(pattern)

        if not matching_keys:
            self.logger.warning(
                "Parsed profile not found — candidate_id=%s", candidate_id
            )
            return None

        raw = self.r.get(matching_keys[0])
        if raw is None:
            return None
        return json.loads(raw)

    def _check_ats_score(
        self, score: float, rules: EligibilityRules
    ) -> EligibilityCheck:
        """
        Check whether the candidate's ATS final score meets the minimum threshold.

        Args:
            score: The candidate's final ATS score (0-100).
            rules: The job's eligibility rules.

        Returns:
            EligibilityCheck with rule="ats_score".
        """
        passed = score >= rules.min_ats_score
        return EligibilityCheck(
            rule="ats_score",
            passed=passed,
            value=score,
            threshold=rules.min_ats_score,
            note="" if passed else f"Score {score:.1f} below minimum {rules.min_ats_score}",
        )

    def _check_skill_score(
        self, skill_score: float, rules: EligibilityRules
    ) -> EligibilityCheck:
        """
        Check whether the candidate's skill sub-score meets the minimum threshold.

        Uses sub_scores.skills from the ATS result — no re-extraction needed.

        Args:
            skill_score: The candidate's skill sub-score (0-100).
            rules: The job's eligibility rules.

        Returns:
            EligibilityCheck with rule="skill_score".
        """
        passed = skill_score >= rules.min_skill_score
        return EligibilityCheck(
            rule="skill_score",
            passed=passed,
            value=skill_score,
            threshold=rules.min_skill_score,
            note="" if passed else f"Skill score {skill_score:.1f} below minimum {rules.min_skill_score}",
        )

    def _check_experience(
        self, exp_months: int, rules: EligibilityRules
    ) -> EligibilityCheck:
        """
        Check whether the candidate's experience falls within the allowed range.

        Args:
            exp_months: Candidate's total experience in months (from parsed_profile).
            rules: The job's eligibility rules.

        Returns:
            EligibilityCheck with rule="experience_range".
        """
        passed = rules.min_experience_months <= exp_months <= rules.max_experience_months
        note = ""
        if exp_months < rules.min_experience_months:
            note = f"Experience {exp_months}m below minimum {rules.min_experience_months}m"
        elif exp_months > rules.max_experience_months:
            note = f"Experience {exp_months}m exceeds maximum {rules.max_experience_months}m"

        return EligibilityCheck(
            rule="experience_range",
            passed=passed,
            value=exp_months,
            threshold=f"{rules.min_experience_months}–{rules.max_experience_months} months",
            note=note,
        )

    def _check_location(
        self, location: str, rules: EligibilityRules
    ) -> EligibilityCheck:
        """
        Check whether the candidate's location satisfies job constraints.

        If location_constraints is empty, the check always passes.
        Comparison is case-insensitive.

        Args:
            location: Candidate's location string from parsed_profile.
            rules: The job's eligibility rules.

        Returns:
            EligibilityCheck with rule="location".
        """
        if not rules.location_constraints:
            return EligibilityCheck(
                rule="location",
                passed=True,
                value=location,
                threshold=rules.location_constraints,
                note="No location restriction",
            )

        allowed = [loc.lower() for loc in rules.location_constraints]
        passed = location.lower() in allowed
        return EligibilityCheck(
            rule="location",
            passed=passed,
            value=location,
            threshold=rules.location_constraints,
            note="" if passed else f"Location '{location}' not in allowed list {rules.location_constraints}",
        )

    def _check_availability(
        self, profile: dict, rules: EligibilityRules
    ) -> EligibilityCheck:
        """
        Check whether the candidate meets the availability requirement.

        If availability_required is False, the check always passes.
        Otherwise reads is_actively_looking from the parsed profile.

        Args:
            profile: The candidate's parsed profile dict from Redis.
            rules: The job's eligibility rules.

        Returns:
            EligibilityCheck with rule="availability".
        """
        if not rules.availability_required:
            return EligibilityCheck(
                rule="availability",
                passed=True,
                value=profile.get("is_actively_looking", False),
                threshold=rules.availability_required,
                note="Availability check not required for this job",
            )

        is_available = profile.get("is_actively_looking", False)
        return EligibilityCheck(
            rule="availability",
            passed=is_available,
            value=is_available,
            threshold=True,
            note="" if is_available else "Candidate is not actively looking",
        )

    def _determine_status(
        self, ats_score: float, checks: List[EligibilityCheck], rules: EligibilityRules
    ) -> str:
        """
        Determine the final eligibility status from the rule checks.

        Priority order:
          1. Hard rejects: experience, location, availability failures → "Rejected"
          2. Both ATS score and skill score pass → "Eligible"
          3. ATS score within review band → "Review"
          4. Otherwise → "Rejected"

        Args:
            ats_score: The candidate's final ATS score.
            checks: List of all EligibilityCheck results.
            rules: The job's eligibility rules.

        Returns:
            str: "Eligible", "Review", or "Rejected".
        """
        checks_by_rule = {c.rule: c for c in checks}

        # Hard rejects — order matters
        if not checks_by_rule.get("experience_range", EligibilityCheck(rule="experience_range", passed=True, value=0, threshold=0)).passed:
            return "Rejected"
        if not checks_by_rule.get("location", EligibilityCheck(rule="location", passed=True, value="", threshold="")).passed:
            return "Rejected"
        if not checks_by_rule.get("availability", EligibilityCheck(rule="availability", passed=True, value=False, threshold=False)).passed:
            return "Rejected"

        ats_check_passed = checks_by_rule.get(
            "ats_score", EligibilityCheck(rule="ats_score", passed=False, value=0, threshold=0)
        ).passed
        skill_check_passed = checks_by_rule.get(
            "skill_score", EligibilityCheck(rule="skill_score", passed=False, value=0, threshold=0)
        ).passed

        if ats_check_passed and skill_check_passed:
            return "Eligible"

        if ats_score >= (rules.min_ats_score - rules.review_band):
            return "Review"

        return "Rejected"

    def evaluate(self, candidate_id: str, job_id: str) -> Optional[EligibilityResult]:
        """
        Orchestrate a full eligibility evaluation for one candidate/job pair.

        Steps:
          1. Load rules (defaults if missing)
          2. Load ATS score — returns None if missing
          3. Hard reject if must_haves_met=False
          4. Load parsed profile — returns None if missing
          5. Extract values safely via .get()
          6. Run all 5 rule checks
          7. Determine status
          8. Build and store EligibilityResult in Redis
          9. Return EligibilityResult

        Args:
            candidate_id: The candidate identifier.
            job_id: The job identifier.

        Returns:
            EligibilityResult or None if required Redis data is absent.
        """
        rules = self.load_rules(job_id)

        ats_score_dict = self.load_ats_score(candidate_id, job_id)
        if ats_score_dict is None:
            return None

        # Hard reject if ATS must-have filter already failed
        must_haves_met: bool = ats_score_dict.get("must_haves_met", True)
        if not must_haves_met:
            self.logger.info(
                "Hard reject — must_haves_met=False — candidate_id=%s, job_id=%s",
                candidate_id,
                job_id,
            )
            result = EligibilityResult(
                candidate_id=candidate_id,
                job_id=job_id,
                eligibility_status="Rejected",
                final_score=ats_score_dict.get("final_score", 0.0),
                skill_score=ats_score_dict.get("sub_scores", {}).get("skills", 0.0),
                experience_months=0,
                checks=[
                    EligibilityCheck(
                        rule="must_haves_met",
                        passed=False,
                        value=False,
                        threshold=True,
                        note="ATS must-have filter failed — candidate rejected before eligibility scoring",
                    )
                ],
                evaluated_at=datetime.now(timezone.utc).isoformat(),
                notes="Rejected at must-have gate before eligibility rules applied",
            )
            redis_key = f"eligibility:{candidate_id}:{job_id}"
            self.r.set(redis_key, result.model_dump_json())
            return result

        # Safe extraction — never dot notation on Redis data
        profile_dict = self.load_parsed_profile(candidate_id)
        if profile_dict is None:
            return None

        # Safe extraction — never dot notation on Redis data
        final_score: float = ats_score_dict.get("final_score", 0.0)
        skill_score: float = ats_score_dict.get("sub_scores", {}).get("skills", 0.0)
        exp_months: int = profile_dict.get("total_experience_months", 0)
        location: str = profile_dict.get("location", "")

        checks = [
            self._check_ats_score(final_score, rules),
            self._check_skill_score(skill_score, rules),
            self._check_experience(exp_months, rules),
            self._check_location(location, rules),
            self._check_availability(profile_dict, rules),
        ]

        status = self._determine_status(final_score, checks, rules)

        result = EligibilityResult(
            candidate_id=candidate_id,
            job_id=job_id,
            eligibility_status=status,
            final_score=final_score,
            skill_score=skill_score,
            experience_months=exp_months,
            checks=checks,
            evaluated_at=datetime.now(timezone.utc).isoformat(),
        )

        redis_key = f"eligibility:{candidate_id}:{job_id}"
        self.r.set(redis_key, result.model_dump_json())

        self.logger.info(
            "Eligibility evaluated — candidate_id=%s, job_id=%s, status=%s, score=%.2f",
            candidate_id,
            job_id,
            status,
            final_score,
        )

        return result

    def evaluate_batch(
        self, candidate_job_pairs: list[tuple]
    ) -> List[EligibilityResult]:
        """
        Evaluate eligibility for a list of (candidate_id, job_id) pairs.

        Skips any pair where evaluate() returns None (missing data).

        Args:
            candidate_job_pairs: List of (candidate_id, job_id) tuples.

        Returns:
            List of EligibilityResult for all successfully evaluated pairs.
        """
        results: List[EligibilityResult] = []

        for candidate_id, job_id in candidate_job_pairs:
            result = self.evaluate(candidate_id, job_id)
            if result is None:
                self.logger.warning(
                    "Skipping pair — candidate_id=%s, job_id=%s (missing data)",
                    candidate_id,
                    job_id,
                )
                continue
            results.append(result)

        return results