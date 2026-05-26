"""
ATS Scoring Engine for Zecpath.
Scores a candidate against a job description using
deterministic matching across skills, experience,
education, and certifications.
"""

import re
import json
from typing import Optional

from utils.logger import get_logger
from utils.schemas import SkillObject, JobProfile, ScoringWeights
from ats_engine.experience_parser import ExperienceParser, QE_ROLE_GROUPS
from parsers.education_parser import EducationParser, QE_CERTIFICATIONS
from scoring.semantic_scorer import SemanticScorer
from scoring.role_weights import get_role_weights


# ─── Module Level Constants ────────────────────────────────────────────────────

SHORTLIST_THRESHOLD: float = 80.0

MATCH_LABELS: dict[str, str] = {
    "strong": "Strong Match",
    "moderate": "Moderate Match",
    "weak": "Weak Match",
    "rejected": "Rejected",
}

LEVEL_SCORE_MAP: dict[str, float] = {
    "expert": 1.0,
    "advanced": 0.85,
    "intermediate": 0.70,
    "beginner": 0.50,
}

DEFAULT_WEIGHTS: dict[str, int] = {
    "skills": 45,
    "experience": 35,
    "education": 10,
    "certifications": 10,
}


# ─── ATSScorer Class ───────────────────────────────────────────────────────────

class ATSScorer:
    """
    Deterministic ATS scoring engine for the Zecpath QE hiring platform.

    Scores a candidate profile against a job profile across four dimensions:
    skills, experience, education, and certifications. Applies configurable
    weights and a shortlist threshold to produce a final hiring decision.
    """

    def __init__(self) -> None:
        """Initialise parsers and logger."""
        self.experience_parser = ExperienceParser()
        self.education_parser = EducationParser()
        self.logger = get_logger(__name__)
        self.semantic_scorer = SemanticScorer()

    # ── Public API ─────────────────────────────────────────────────────────────

    def score(
    self,
    segmented_resume: dict,
    candidate_profile,
    job_profile: dict,
    jd_raw_text: str = "",
) -> dict:
        """
        Main scoring entry point. Produces a structured result dict with a
        final weighted score, sub-scores, shortlist decision, and audit trail.

        Args:
            candidate_skills: Skill dicts from SkillExtractor.extract().
                Each has: name, level, confidence, is_primary_skill, category.
            candidate_experiences: Experience dicts from ExperienceParser.parse().
                Each has: role_title, duration_months, technologies_used, is_current.
            candidate_education: List of EducationObject instances from Day 11.
            candidate_certifications: Cert dicts from parse_certifications().
                Each has: name, category, is_valid.
            job_profile: Parsed job profile dict. Expected keys: title,
                required_skills, must_have_skills,
                experience_required_min_months,
                experience_required_max_months,
                required_education_level, required_education_field,
                scoring_weights, shortlist_threshold.
            scoring_weights: Optional weight override dict with keys skills,
                experience, education, certifications summing to 100.

        Returns:
            Structured result dict from _build_result().
        """
        job_title = job_profile.get("title", "Unknown Role")
        self.logger.info("Starting ATS scoring for job: '%s'.", job_title)
        # Extract data from candidate_profile
        candidate_skills = [
            s.model_dump() if hasattr(s, "model_dump") else s
            for s in getattr(candidate_profile, "skills", [])
        ]
        candidate_experiences = [
            e.model_dump() if hasattr(e, "model_dump") else e
            for e in getattr(candidate_profile, "experience", [])
        ]
        candidate_education = getattr(candidate_profile, "education", [])
        candidate_certifications = [
            c.model_dump() if hasattr(c, "model_dump") else c
            for c in getattr(candidate_profile, "certifications", [])
        ]

        # 1. Must-have hard filter
        must_haves = job_profile.get("must_have_skills", [])
        if not self._check_must_haves(candidate_skills, must_haves):
            self.logger.warning(
                "Must-have filter failed for '%s' — instant reject.", job_title
            )
            return self._build_result(
                final_score=0.0,
                sub_scores={
                    "skills": 0.0,
                    "experience": 0.0,
                    "education": 0.0,
                    "certifications": 0.0,
                },
                shortlisted=False,
                match_label="rejected",
                must_haves_met=False,
                audit_trail=["Must-have skills not met — candidate rejected."],
                job_profile=job_profile,
            )

        # 2. Resolve weights
        weights = self._resolve_weights(None, job_profile)

        # 3. Score skills
        skills_score, skills_audit = self._score_skills(
            candidate_skills,
            job_profile.get("required_skills", []),
            must_haves,
        )

        # 4. Score experience
        experience_score, exp_audit = self._score_experience(
            candidate_experiences,
            job_title,
            job_profile.get("experience_required_min_months", 0),
            job_profile.get("experience_required_max_months", 9999),
        )

        # 5. Score education
        education_score, edu_audit = self._score_education(
            candidate_education,
            job_profile.get("required_education_level", "bachelors"),
            job_profile.get("required_education_field", []),
        )

        # 6. Score certifications
        cert_score, cert_audit = self._score_certifications(
            candidate_certifications,
            job_profile.get("required_skills", []),
        )
        semantic = self._score_semantic(segmented_resume, jd_raw_text)

        # 7. Weighted final score
        w = {k: v / 100.0 for k, v in weights.items()}
        education_combined = round((education_score * 0.7) + (cert_score * 0.3), 2)
        w = weights  # already resolved earlier in the method
        final_score = round(
            (skills_score     * w.get("skills",     0.35)) +
            (experience_score * w.get("experience", 0.25)) +
            (education_combined * w.get("education", 0.15)) +
            (semantic         * w.get("semantic",   0.25)),
            2,
        )

        # 8. Shortlist and label
        threshold = job_profile.get("shortlist_threshold", SHORTLIST_THRESHOLD)
        shortlisted = final_score >= threshold

        if final_score >= 85:
            match_key = "strong"
        elif final_score >= 70:
            match_key = "moderate"
        elif final_score >= 50:
            match_key = "weak"
        else:
            match_key = "rejected"

        # 9. Compile full audit trail
        audit_trail: list[str] = (
            ["=== Skills ==="]
            + skills_audit
            + ["=== Experience ==="]
            + exp_audit
            + ["=== Education ==="]
            + edu_audit
            + ["=== Certifications ==="]
            + cert_audit
            + [f"Semantic similarity: {semantic}/100"]
            + [f"Education combined (edu*0.7 + cert*0.3): {education_combined}/100"]
            + [f"=== Final Score: {final_score}/100 ==="]
        )

        self.logger.info(
            "Scoring complete — final_score=%.2f, shortlisted=%s, label=%s.",
            final_score, shortlisted, MATCH_LABELS[match_key],
        )

        return self._build_result(
            final_score=final_score,
            sub_scores={
                "skills": round(skills_score, 2),
                "experience": round(experience_score, 2),
                "education": round(education_score, 2),
                "certifications": round(cert_score, 2),
                "semantic": round(semantic, 2),
                "education_combined": education_combined,
            },
            shortlisted=shortlisted,
            match_label=match_key,
            must_haves_met=True,
            audit_trail=audit_trail,
            job_profile=job_profile,
        )

    def classify_match(self, score: float) -> str:
        """
        Classify a numeric score into a human-readable match label.

        Args:
            score: Final ATS score (0.0 – 100.0).

        Returns:
            One of: "Strong Match", "Moderate Match", "Weak Match", "Rejected".
        """
        if score >= 85:
            return MATCH_LABELS["strong"]
        elif score >= 70:
            return MATCH_LABELS["moderate"]
        elif score >= 50:
            return MATCH_LABELS["weak"]
        return MATCH_LABELS["rejected"]

    # ── Hard Filters ───────────────────────────────────────────────────────────

    def _check_must_haves(
        self,
        candidate_skills: list[dict],
        must_have_skills: list[str],
    ) -> bool:
        """
        Verify that the candidate possesses every must-have skill.

        Uses both exact name matching and substring matching to handle
        minor spelling variations.

        Args:
            candidate_skills: List of skill dicts from the extractor.
            must_have_skills: List of required skill name strings.

        Returns:
            True if all must-haves are satisfied, False otherwise.
        """
        if not must_have_skills:
            return True

        candidate_names: set[str] = {
            s.get("name", "").lower() for s in candidate_skills
        }

        missing: list[str] = []
        for must_have in must_have_skills:
            mh_lower = must_have.lower()
            exact_match = mh_lower in candidate_names
            partial_match = any(mh_lower in name for name in candidate_names)
            if not (exact_match or partial_match):
                missing.append(must_have)

        if missing:
            self.logger.warning(
                "Must-have skills missing: %s", missing
            )
            return False

        return True

    # ── Sub-Scorers ────────────────────────────────────────────────────────────

    def _score_skills(
        self,
        candidate_skills: list[dict],
        required_skills: list,
        must_have_skills: list[str],
    ) -> tuple[float, list[str]]:
        """
        Score how well the candidate's skills cover the job's required skills.

        Applies a level multiplier from LEVEL_SCORE_MAP and a primary-skill
        bonus (up to 10 points) for high-confidence matched skills.

        Args:
            candidate_skills: Skill dicts from the extractor.
            required_skills: List of required skill dicts or plain strings.
            must_have_skills: List of must-have skill name strings (unused
                here but kept for signature consistency).

        Returns:
            Tuple of (skills_score 0-100, audit_list).
        """
        if not required_skills:
            return 70.0, ["No required skills specified — default score applied."]

        # Normalise required skills to lowercase strings
        required_names: list[str] = []
        for item in required_skills:
            if isinstance(item, dict):
                required_names.append(item.get("name", "").lower())
            else:
                required_names.append(str(item).lower())

        candidate_name_map: dict[str, dict] = {
            s.get("name", "").lower(): s for s in candidate_skills
        }

        matched: list[str] = []
        missing: list[str] = []
        level_weighted_sum: float = 0.0

        for req in required_names:
            # Exact match first, then partial
            matched_skill: Optional[dict] = candidate_name_map.get(req)
            if matched_skill is None:
                for cname, cskill in candidate_name_map.items():
                    if req in cname or cname in req:
                        matched_skill = cskill
                        break

            if matched_skill:
                level = matched_skill.get("level", "intermediate")
                level_multiplier = LEVEL_SCORE_MAP.get(level, 0.70)
                level_weighted_sum += level_multiplier
                matched.append(matched_skill.get("name", req))
            else:
                missing.append(req)

        total_required = len(required_names)
        match_ratio = len(matched) / total_required if total_required > 0 else 0.0

        # Base score from match ratio weighted by level
        if matched:
            avg_level_multiplier = level_weighted_sum / len(matched)
        else:
            avg_level_multiplier = 0.0
        skills_score = match_ratio * avg_level_multiplier * 100.0

        # Primary skill bonus (max 10 points)
        bonus = 0.0
        for skill in candidate_skills:
            if (
                skill.get("is_primary_skill")
                and skill.get("name", "").lower() in [m.lower() for m in matched]
            ):
                bonus = min(bonus + 2.0, 10.0)

        skills_score = min(100.0, skills_score + bonus)

        audit: list[str] = [
            f"Matched: {len(matched)}/{total_required} required skills.",
            f"Matched skills: {matched}",
            f"Missing skills: {missing}",
            f"Primary skill bonus: {bonus:.1f} points.",
            f"Skills sub-score: {round(skills_score, 2)}/100",
        ]

        self.logger.info(
            "_score_skills(): matched %d/%d, score=%.2f.",
            len(matched), total_required, skills_score,
        )
        return round(skills_score, 2), audit

    def _score_experience(
        self,
        candidate_experiences: list[dict],
        job_title: str,
        min_months: int,
        max_months: int,
    ) -> tuple[float, list[str]]:
        """
        Score the candidate's experience by duration and QE role relevance.

        Duration score tiers:
            >= min_months         → 1.0
            >= min_months * 0.75  → 0.8
            >= min_months * 0.5   → 0.6
            otherwise             → 0.3

        Final = (relevance * 0.6 + duration * 0.4) * 100

        Args:
            candidate_experiences: List of experience dicts.
            job_title: Target role title for relevance scoring.
            min_months: Minimum required experience in months.
            max_months: Maximum expected experience in months.

        Returns:
            Tuple of (experience_score 0-100, audit_list).
        """
        if not candidate_experiences:
            return 0.0, ["No experience data found."]

        total_months = sum(
            e.get("duration_months", 0) for e in candidate_experiences
        )

        relevance_result = self.experience_parser.calculate_relevance_score(
            candidate_experiences, job_title
        )
        relevance_score = relevance_result.get("relevance_score", 0.0)

        # Duration score
        if min_months == 0:
            duration_score = 1.0
        elif total_months >= min_months:
            duration_score = 1.0
        elif total_months >= min_months * 0.75:
            duration_score = 0.8
        elif total_months >= min_months * 0.5:
            duration_score = 0.6
        else:
            duration_score = 0.3

        experience_score = round(
            (relevance_score * 0.6 + duration_score * 0.4) * 100, 2
        )

        audit: list[str] = [
            f"Total experience: {total_months} months.",
            f"Required: {min_months} to {max_months} months.",
            f"Duration score: {duration_score}",
            f"Relevance score: {relevance_score} (QE role match).",
            f"Experience sub-score: {experience_score}/100",
        ]

        self.logger.info(
            "_score_experience(): total=%d months, relevance=%.2f, score=%.2f.",
            total_months, relevance_score, experience_score,
        )
        return experience_score, audit

    def _score_education(
        self,
        candidate_education: list,
        required_level: str,
        required_fields: list[str],
    ) -> tuple[float, list[str]]:
        """
        Score the candidate's education against the job's level and field
        requirements using EducationParser.calculate_education_relevance().

        Args:
            candidate_education: List of EducationObject instances.
            required_level: Minimum required education level string.
            required_fields: List of acceptable fields of study.

        Returns:
            Tuple of (education_score 0-100, audit_list).
        """
        if not candidate_education:
            return 50.0, ["No education data found — default score applied."]

        result = self.education_parser.calculate_education_relevance(
            candidate_education,
            required_level,
            required_fields,
        )

        education_score = round(
            result.get("education_relevance_score", 0.0) * 100, 2
        )

        audit: list[str] = [
            f"Required level: {required_level}.",
            f"Highest level found: {result.get('highest_level_found', 'unknown')}.",
            f"Field matched: {result.get('field_matched', False)}.",
            f"Education sub-score: {education_score}/100",
        ]

        self.logger.info(
            "_score_education(): level=%s, field_matched=%s, score=%.2f.",
            result.get("highest_level_found"), result.get("field_matched"),
            education_score,
        )
        return education_score, audit

    def _score_certifications(
        self,
        candidate_certifications: list[dict],
        required_skills: list,
    ) -> tuple[float, list[str]]:
        """
        Score certifications by relevance to the required QE categories.

        Derives required categories by matching required skill names against
        QE_CERTIFICATIONS keys. Applies a count bonus for 1+ or 3+ certs.

        Args:
            candidate_certifications: List of cert dicts with name/category/is_valid.
            required_skills: Required skills list (dicts or strings) used to
                infer required cert categories.

        Returns:
            Tuple of (cert_score 0-100, audit_list).
        """
        if not candidate_certifications:
            return 40.0, ["No certifications found — partial score applied."]

        # Derive required categories from required skills
        required_categories: set[str] = set()
        for item in required_skills:
            skill_name = (
                item.get("name", "").lower()
                if isinstance(item, dict)
                else str(item).lower()
            )
            for cert_key, meta in QE_CERTIFICATIONS.items():
                if skill_name in cert_key or cert_key in skill_name:
                    cat = meta.get("category")
                    if cat:
                        required_categories.add(cat)

        if not required_categories:
            required_categories = {"methodology", "quality_standard"}

        result = self.education_parser.calculate_certification_relevance(
            candidate_certifications,
            list(required_categories),
        )
        cert_relevance = result.get("certification_relevance_score", 0.0)
        relevant_count = result.get("relevant_certifications", 0)

        # Count bonus
        total_certs = len(candidate_certifications)
        if total_certs >= 3:
            bonus = 10.0
        elif total_certs >= 1:
            bonus = 5.0
        else:
            bonus = 0.0

        cert_score = round(min(100.0, cert_relevance * 90.0 + bonus), 2)

        audit: list[str] = [
            f"Total certifications: {total_certs}.",
            f"Required categories: {sorted(required_categories)}.",
            f"Relevant certifications: {relevant_count}.",
            f"Certification sub-score: {cert_score}/100",
        ]

        self.logger.info(
            "_score_certifications(): total=%d, relevant=%d, score=%.2f.",
            total_certs, relevant_count, cert_score,
        )
        return cert_score, audit
    
    def _score_semantic(self, segmented_resume: dict, jd_text: str) -> float:
        """
    Compute semantic similarity between resume sections and JD text.

    Delegates to SemanticScorer.score_sections(), which extracts only
    the skills and experience sections before scoring.

    Args:
        segmented_resume: Day 8 structured resume dict.
        jd_text: Raw JD plain text.

    Returns:
        Semantic similarity score 0.0–100.0.
    """
        result = self.semantic_scorer.score_sections(segmented_resume, jd_text)
        self.logger.debug("Semantic score: %.2f", result)
        return result

    # ── Result Builder ─────────────────────────────────────────────────────────

    def _build_result(
        self,
        final_score: float,
        sub_scores: dict,
        shortlisted: bool,
        match_label: str,
        must_haves_met: bool,
        audit_trail: list[str],
        job_profile: dict,
    ) -> dict:
        """
        Assemble and return the standardised scoring result dict.

        Args:
            final_score: Weighted composite score (0.0 – 100.0).
            sub_scores: Dict of individual dimension scores.
            shortlisted: Whether the candidate clears the threshold.
            match_label: One of the MATCH_LABELS keys.
            must_haves_met: Whether the must-have filter passed.
            audit_trail: Combined list of audit strings from all scorers.
            job_profile: The original job profile dict.

        Returns:
            Structured result dict.
        """
        weights = self._resolve_weights(None, job_profile)
        threshold = job_profile.get("shortlist_threshold", SHORTLIST_THRESHOLD)

        return {
            "final_score": final_score,
            "match_label": MATCH_LABELS.get(match_label, match_label),
            "shortlisted": shortlisted,
            "must_haves_met": must_haves_met,
            "sub_scores": sub_scores,
            "weights_used": weights,
            "shortlist_threshold": threshold,
            "job_title": job_profile.get("title", "Unknown"),
            "audit_trail": audit_trail,
        }

    # ── Private Utilities ──────────────────────────────────────────────────────

    def _resolve_weights(
    self,
    scoring_weights: Optional[dict],
    job_profile: dict,
) -> dict:
        """
    Resolve the scoring weight dict using the following priority order:

    1. ``scoring_weights`` argument — explicit recruiter override.
    2. ``get_role_weights(job_profile title)`` — role-based registry lookup.
    3. Hardcoded QE defaults — final fallback.

    Normalises the resolved dict so values always sum to 1.0.

    Args:
        scoring_weights: Caller-supplied override dict, or None.
        job_profile: Job profile dict used for title-based lookup.

    Returns:
        Normalised weight dict with keys: skills, experience, education,
        semantic — each a float summing to 1.0.
    """
        if scoring_weights:
            weights = dict(scoring_weights)
        else:
            job_title = job_profile.get("title", "")
            weights = get_role_weights(job_title)  # falls back to DEFAULT_WEIGHTS internally

        # Normalise so values always sum to 1.0
        total = sum(weights.values())
        if total > 0 and abs(total - 1.0) > 1e-6:
            weights = {k: round(v / total, 6) for k, v in weights.items()}

        return weights
    def generate_candidate_score(
    candidate_profile,
    job_profile: dict,
    segmented_resume: dict,
    jd_raw_text: str = "",
) -> dict:
        """
    Unified public entry point for ATS scoring.

    Instantiates a fresh ATSScorer and delegates to its score() method.
    This is the single callable for pipeline orchestration and matches
    the manager-expected interface for Day 13.

    Args:
        candidate_profile: CandidateProfile instance (Day 4 schema).
        job_profile: Parsed job profile dict.
        segmented_resume: Day 8 structured resume dict.
        jd_raw_text: Raw JD text for semantic scoring. Defaults to ``""``.

    Returns:
        Structured scoring result dict from ATSScorer.score().
    """
        scorer = ATSScorer()
        return scorer.score(segmented_resume, candidate_profile, job_profile, jd_raw_text)