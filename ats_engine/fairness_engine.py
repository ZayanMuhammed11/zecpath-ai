"""
ats_engine/fairness_engine.py

Day 15 — Fairness, Normalization & Bias Reduction for the Zecpath AI hiring platform.
Provides score normalization, sensitive data masking, keyword bias reduction,
bias indicator evaluation, and a full fairness pipeline for QE candidate results.
"""

from utils.logger import get_logger

logger = get_logger(__name__)


def normalize_scores(candidates: list[dict]) -> list[dict]:
    """
    Apply min-max normalization to the final_score of each candidate.

    Normalized score is scaled to the range [0, 100] and stored under
    the key 'normalized_score' (float, rounded to 2 decimal places).

    If all candidates share the same final_score, every normalized_score
    is set to 100.0 and a debug warning is logged.

    Args:
        candidates: List of candidate result dicts (Day 13 format).

    Returns:
        The same list with 'normalized_score' added to each dict.
        Returns an empty list if the input list is empty.
    """
    if not candidates:
        return []

    scores: list[float] = [c["final_score"] for c in candidates]
    min_score: float = min(scores)
    max_score: float = max(scores)

    logger.info(
        "Normalizing scores — min: %.2f, max: %.2f, total candidates: %d",
        min_score,
        max_score,
        len(candidates),
    )

    if max_score == min_score:
        logger.debug(
            "All candidate final_scores are identical (%.2f). "
            "Setting normalized_score=100.0 for all.",
            min_score,
        )
        for candidate in candidates:
            candidate["normalized_score"] = 100.0
        return candidates

    for candidate in candidates:
        raw: float = candidate["final_score"]
        normalized: float = round(((raw - min_score) / (max_score - min_score)) * 100, 2)
        candidate["normalized_score"] = normalized

    return candidates


def mask_sensitive_data(candidate: dict) -> dict:
    """
    Mask personally identifiable and bias-prone fields in a candidate dict.

    Fields masked: name, full_name, gender, age, photo, date_of_birth,
    marital_status, nationality, religion.

    Location is intentionally NOT masked — it is a job-relevant field
    in Quality Engineering hiring (on-site/hybrid proximity matters).

    Missing fields are skipped silently without raising errors.

    Args:
        candidate: A candidate result dict.

    Returns:
        The same dict with sensitive fields set to "MASKED" and
        'bias_masking_applied' set to True.
    """
    sensitive_fields: list[str] = [
        "name",
        "full_name",
        "gender",
        "age",
        "photo",
        "date_of_birth",
        "marital_status",
        "nationality",
        "religion",
    ]

    masked_fields: list[str] = []

    for field in sensitive_fields:
        if field in candidate:
            candidate[field] = "MASKED"
            masked_fields.append(field)

    candidate["bias_masking_applied"] = True

    logger.debug("Masked sensitive fields: %s", masked_fields)

    return candidate


def reduce_keyword_bias(
    skill_score: float,
    semantic_score: float,
    keyword_weight: float = 0.4,
    semantic_weight: float = 0.6,
) -> float:
    """
    Blend keyword-based skill score and semantic score to reduce keyword stuffing bias.

    Formula:
        adjusted = (semantic_weight * semantic_score) + (keyword_weight * skill_score)

    Args:
        skill_score:      Raw keyword/skill match score (0–100).
        semantic_score:   Semantic similarity score (0–100).
        keyword_weight:   Weight applied to skill_score (default 0.4).
        semantic_weight:  Weight applied to semantic_score (default 0.6).

    Returns:
        Blended adjusted score, rounded to 2 decimal places.

    Raises:
        ValueError: If keyword_weight + semantic_weight does not equal 1.0.
    """
    if round(keyword_weight + semantic_weight, 10) != 1.0:
        raise ValueError(
            f"keyword_weight ({keyword_weight}) + semantic_weight ({semantic_weight}) "
            f"must equal 1.0, got {keyword_weight + semantic_weight}."
        )

    adjusted: float = round(
        (semantic_weight * semantic_score) + (keyword_weight * skill_score), 2
    )

    logger.debug(
        "reduce_keyword_bias — skill_score: %.2f, semantic_score: %.2f, "
        "keyword_weight: %.2f, semantic_weight: %.2f → adjusted: %.2f",
        skill_score,
        semantic_score,
        keyword_weight,
        semantic_weight,
        adjusted,
    )

    return adjusted


def evaluate_bias_indicators(candidate: dict) -> dict:
    """
    Evaluate a candidate result dict for known bias risk signals.

    Checks performed:
        - keyword_dominance:      skills score exceeds semantic score by > 30
                                  (possible keyword stuffing).
        - experience_gap_penalty: experience sub-score < 40
                                  (heavy penalty for experience gaps).
        - education_prestige_bias: education > 90 while skills < 50
                                  (education compensating for low skills).
        - semantic_under_weight:  semantic weight in weights_used < 0.15
                                  (semantic scoring given too little influence).

    Bias risk level:
        0 True indicators  → "low"
        1–2 True indicators → "medium"
        3–4 True indicators → "high"

    Args:
        candidate: A candidate result dict (Day 13 format).

    Returns:
        A bias_report dict containing candidate_id, bias_indicators, and
        bias_risk_level.
    """
    sub_scores: dict = candidate.get("sub_scores", {})
    weights_used: dict = candidate.get("weights_used", {})
    candidate_id: str = str(candidate.get("candidate_id", "unknown"))

    skill_score: float = sub_scores.get("skills", 0.0)
    semantic_score: float = sub_scores.get("semantic", 0.0)
    experience_score: float = sub_scores.get("experience", 0.0)
    education_score: float = sub_scores.get("education", 0.0)

    bias_indicators: dict[str, bool] = {
        "keyword_dominance": (skill_score - semantic_score) > 30,
        "experience_gap_penalty": experience_score < 40,
        "education_prestige_bias": education_score > 90 and skill_score < 50,
        "semantic_under_weight": weights_used.get("semantic", 0) < 0.15,
    }

    true_count: int = sum(bias_indicators.values())

    if true_count == 0:
        bias_risk_level = "low"
    elif true_count <= 2:
        bias_risk_level = "medium"
    else:
        bias_risk_level = "high"

    logger.info(
        "evaluate_bias_indicators — candidate_id: %s, bias_risk_level: %s",
        candidate_id,
        bias_risk_level,
    )

    return {
        "candidate_id": candidate_id,
        "bias_indicators": bias_indicators,
        "bias_risk_level": bias_risk_level,
    }


def generate_fair_score(candidate: dict) -> dict:
    """
    Generate a bias-reduced fair_score for a candidate by blending
    keyword skill score and semantic score via reduce_keyword_bias().

    The result is stored in the candidate dict under the key 'fair_score'.

    Args:
        candidate: A candidate result dict (Day 13 format).

    Returns:
        The same candidate dict with 'fair_score' added.
    """
    sub_scores: dict = candidate.get("sub_scores", {})
    skill_score: float = sub_scores.get("skills", 0.0)
    semantic_score: float = sub_scores.get("semantic", 0.0)

    fair_score: float = reduce_keyword_bias(skill_score, semantic_score)
    candidate["fair_score"] = fair_score

    logger.debug(
        "generate_fair_score — final_score: %.2f, fair_score: %.2f",
        candidate.get("final_score", 0.0),
        fair_score,
    )

    return candidate


def apply_fairness_pipeline(candidates: list[dict]) -> list[dict]:
    """
    Apply the full fairness pipeline to a list of candidate result dicts.

    Pipeline steps per candidate:
        1. generate_fair_score()     — bias-reduced score blending
        2. evaluate_bias_indicators() — bias risk signal detection
        3. Attach bias_report to candidate dict

    After per-candidate processing:
        4. normalize_scores()        — min-max normalization across the list

    Args:
        candidates: List of candidate result dicts (Day 13 format).

    Returns:
        Enriched candidate list with 'fair_score', 'bias_report', and
        'normalized_score' set on every candidate.
    """
    for candidate in candidates:
        generate_fair_score(candidate)
        bias_report: dict = evaluate_bias_indicators(candidate)
        candidate["bias_report"] = bias_report

    normalize_scores(candidates)

    logger.info(
        "apply_fairness_pipeline complete — total candidates processed: %d",
        len(candidates),
    )

    return candidates