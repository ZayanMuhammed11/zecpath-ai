"""
Candidate Ranking and Shortlisting Engine for Zecpath ATS.

Provides deterministic ranking, status classification, and recruiter
summary generation for a list of scored candidates. No LLM calls.
"""

from utils.logger import get_logger

logger = get_logger(__name__)


# ─── Module-Level Constants ────────────────────────────────────────────────────

THRESHOLDS: dict[str, int] = {
    "shortlist": 75,
    "review": 50,
}


# ─── Functions ─────────────────────────────────────────────────────────────────

def rank_candidates(candidates: list[dict]) -> list[dict]:
    """
    Sort a list of scored candidate dicts descending by ``final_score``
    and assign a 1-based ``rank`` key to each entry.

    Args:
        candidates: List of candidate result dicts, each containing at
            minimum a ``final_score`` float key.

    Returns:
        New list sorted descending by ``final_score`` with ``rank`` keys
        assigned. Returns ``[]`` when the input list is empty.
    """
    if not candidates:
        logger.debug("rank_candidates() received an empty list — returning [].")
        return []

    sorted_candidates = sorted(
        candidates,
        key=lambda c: c.get("final_score", 0.0),
        reverse=True,
    )

    for rank, candidate in enumerate(sorted_candidates, start=1):
        candidate["rank"] = rank

    logger.debug(
        "rank_candidates(): ranked %d candidates.", len(sorted_candidates)
    )
    return sorted_candidates


def classify_candidate(score: float) -> str:
    """
    Classify a candidate's numeric ATS score into a status string.

    Thresholds (from module-level THRESHOLDS):
        >= 75 → ``"Shortlisted"``
        >= 50 → ``"Review"``
        < 50  → ``"Rejected"``

    Args:
        score: The candidate's final ATS score (0.0 – 100.0).

    Returns:
        One of ``"Shortlisted"``, ``"Review"``, or ``"Rejected"``.
    """
    if score >= THRESHOLDS["shortlist"]:
        return "Shortlisted"
    elif score >= THRESHOLDS["review"]:
        return "Review"
    return "Rejected"


def apply_shortlisting(candidates: list[dict]) -> list[dict]:
    """
    Annotate each candidate dict with a ``status`` key derived from
    their ``final_score`` via ``classify_candidate()``.

    Modifies each candidate dict in-place and returns the same list.

    Args:
        candidates: List of candidate result dicts with ``final_score`` keys.

    Returns:
        The same list with ``status`` set on every entry.
    """
    counts: dict[str, int] = {"Shortlisted": 0, "Review": 0, "Rejected": 0}

    for candidate in candidates:
        score = candidate.get("final_score", 0.0)
        status = classify_candidate(score)
        candidate["status"] = status
        counts[status] += 1

    logger.info(
        "apply_shortlisting(): Shortlisted=%d, Review=%d, Rejected=%d.",
        counts["Shortlisted"],
        counts["Review"],
        counts["Rejected"],
    )
    return candidates


def get_top_candidates(candidates: list[dict], top_n: int = 5) -> list[dict]:
    """
    Return the first ``top_n`` candidates from an already-ranked list.

    If the list is shorter than ``top_n``, the entire list is returned.

    Args:
        candidates: Ranked and classified candidate list (output of
            ``apply_shortlisting(rank_candidates(...))``.
        top_n: Maximum number of candidates to return. Defaults to 5.

    Returns:
        Slice of the input list containing at most ``top_n`` entries.
    """
    result = candidates[:top_n]
    logger.debug(
        "get_top_candidates(): returning %d of %d requested (total available: %d).",
        len(result),
        top_n,
        len(candidates),
    )
    return result


def generate_recruiter_summary(
    candidates: list[dict],
    job_id: str = "",
) -> dict:
    """
    Build a clean recruiter-facing summary from a fully ranked and
    classified candidate list.

    Strips verbose fields (``audit_trail``, ``sub_scores``) from the
    top-candidates view. Only ``"Shortlisted"`` and ``"Review"``
    candidates appear in ``top_candidates``; rejected entries are
    excluded from that view but counted in ``summary``.

    Args:
        candidates: Fully ranked and classified candidate list.
        job_id: Optional job identifier string for the summary header.

    Returns:
        Dict with keys ``job_id``, ``summary`` (counts), and
        ``top_candidates`` (slim candidate records, ordered by rank).
    """
    total = len(candidates)
    shortlisted_count = sum(
        1 for c in candidates if c.get("status") == "Shortlisted"
    )
    review_count = sum(
        1 for c in candidates if c.get("status") == "Review"
    )
    rejected_count = sum(
        1 for c in candidates if c.get("status") == "Rejected"
    )

    # Build slim records — only Shortlisted and Review, ordered by rank
    top_candidates: list[dict] = [
        {
            "candidate_id": c.get("candidate_id", ""),
            "final_score": c.get("final_score", 0.0),
            "match_label": c.get("match_label", ""),
            "status": c.get("status", ""),
            "rank": c.get("rank", 0),
        }
        for c in candidates
        if c.get("status") in {"Shortlisted", "Review"}
    ]

    # Already ordered by rank from rank_candidates(), but sort defensively
    top_candidates.sort(key=lambda c: c["rank"])

    return {
        "job_id": job_id,
        "summary": {
            "total_candidates": total,
            "shortlisted": shortlisted_count,
            "review": review_count,
            "rejected": rejected_count,
        },
        "top_candidates": top_candidates,
    }


def ranking_pipeline(
    candidates: list[dict],
    job_id: str = "",
    top_n: int = 5,
) -> dict:
    """
    Execute the full ranking and shortlisting pipeline in one call.

    Pipeline order:
        1. ``rank_candidates()``   — sort and assign ranks
        2. ``apply_shortlisting()`` — classify and annotate status
        3. ``get_top_candidates()`` — slice top N
        4. ``generate_recruiter_summary()`` — build clean summary

    Args:
        candidates: List of raw scored candidate dicts (Day 13 output).
        job_id: Optional job identifier passed through to the summary.
        top_n: Number of top candidates to include in the slice.

    Returns:
        Dict with keys:
            ``ranked_list``       — full list with rank and status keys
            ``top_candidates``    — top N slice
            ``recruiter_summary`` — clean summary dict
    """
    ranked = rank_candidates(candidates)
    classified = apply_shortlisting(ranked)
    top = get_top_candidates(classified, top_n=top_n)
    summary = generate_recruiter_summary(classified, job_id=job_id)

    logger.info(
        "ranking_pipeline(): complete — job_id='%s', total candidates=%d.",
        job_id,
        len(classified),
    )

    return {
        "ranked_list": classified,
        "top_candidates": top,
        "recruiter_summary": summary,
    }