"""
Unit tests for ats_engine.ranking_engine.

All tests are fully deterministic — no mocking, no LLM calls, no I/O.

Run with:
    pytest tests/test_ranking_engine.py -v
"""

from ats_engine.ranking_engine import (
    apply_shortlisting,
    classify_candidate,
    generate_recruiter_summary,
    get_top_candidates,
    rank_candidates,
    ranking_pipeline,
)


# ─── Helpers ───────────────────────────────────────────────────────────────────

def make_candidate(
    candidate_id: str,
    final_score: float,
    match_label: str = "Moderate Match",
) -> dict:
    """
    Build a minimal candidate result dict matching Day 13 output format.

    Args:
        candidate_id: Unique string identifier for the candidate.
        final_score: ATS final score (0.0 – 100.0).
        match_label: Human-readable match label string.

    Returns:
        Candidate dict with the keys produced by ATSScorer.score().
    """
    return {
        "candidate_id": candidate_id,
        "final_score": final_score,
        "match_label": match_label,
        "shortlisted": final_score >= 75.0,
        "must_haves_met": True,
        "sub_scores": {
            "skills": final_score,
            "experience": final_score,
            "education": final_score,
            "certifications": final_score,
            "semantic": final_score,
            "education_combined": final_score,
        },
        "weights_used": {
            "skills": 0.35,
            "experience": 0.30,
            "education": 0.10,
            "semantic": 0.25,
        },
        "shortlist_threshold": 75.0,
        "job_title": "Quality Engineer",
        "audit_trail": ["Test audit entry."],
    }


def make_candidate_pool() -> list[dict]:
    """
    Return a realistic pool of 5 scored candidates covering all three
    status zones (Shortlisted, Review, Rejected).
    """
    return [
        make_candidate("C001", 88.5, "Strong Match"),
        make_candidate("C002", 45.0, "Weak Match"),
        make_candidate("C003", 76.0, "Moderate Match"),
        make_candidate("C004", 30.0, "Rejected"),
        make_candidate("C005", 62.0, "Moderate Match"),
    ]


# ─── Tests ─────────────────────────────────────────────────────────────────────

def test_rank_candidates_sorts_descending():
    """
    rank_candidates() must sort the list by final_score descending so
    the highest-scoring candidate appears first.
    """
    candidates = make_candidate_pool()
    ranked = rank_candidates(candidates)

    scores = [c["final_score"] for c in ranked]
    assert scores == sorted(scores, reverse=True), (
        f"Expected descending order, got: {scores}"
    )


def test_rank_candidates_assigns_ranks_from_one():
    """
    rank_candidates() must assign rank=1 to the first (highest-scoring)
    candidate and increment by 1 for each subsequent entry.
    """
    candidates = make_candidate_pool()
    ranked = rank_candidates(candidates)

    ranks = [c["rank"] for c in ranked]
    expected = list(range(1, len(ranked) + 1))
    assert ranks == expected, (
        f"Expected ranks {expected}, got {ranks}"
    )


def test_rank_candidates_empty_list_returns_empty():
    """
    rank_candidates() must return an empty list without raising any
    exception when given an empty input.
    """
    result = rank_candidates([])

    assert result == [], (
        f"Expected [], got {result}"
    )


def test_classify_candidate_all_zones():
    """
    classify_candidate() must return the correct status string for scores
    in each of the three classification zones.
    """
    assert classify_candidate(90.0) == "Shortlisted", (
        f"Expected 'Shortlisted' for 90.0, got '{classify_candidate(90.0)}'"
    )
    assert classify_candidate(60.0) == "Review", (
        f"Expected 'Review' for 60.0, got '{classify_candidate(60.0)}'"
    )
    assert classify_candidate(30.0) == "Rejected", (
        f"Expected 'Rejected' for 30.0, got '{classify_candidate(30.0)}'"
    )


def test_apply_shortlisting_sets_status_on_all():
    """
    apply_shortlisting() must set a ``status`` key on every candidate
    in the list, with no entries missing the key.
    """
    candidates = make_candidate_pool()
    result = apply_shortlisting(candidates)

    for candidate in result:
        assert "status" in candidate, (
            f"Expected 'status' key on candidate {candidate.get('candidate_id')}"
        )
        assert candidate["status"] in {"Shortlisted", "Review", "Rejected"}, (
            f"Unexpected status value: '{candidate['status']}'"
        )


def test_get_top_candidates_returns_correct_n():
    """
    get_top_candidates() must return exactly top_n items when the list
    is longer than top_n, and the full list when it is shorter.
    """
    candidates = rank_candidates(make_candidate_pool())

    top3 = get_top_candidates(candidates, top_n=3)
    assert len(top3) == 3, (
        f"Expected 3 candidates, got {len(top3)}"
    )

    # When top_n exceeds available candidates, return entire list
    top10 = get_top_candidates(candidates, top_n=10)
    assert len(top10) == len(candidates), (
        f"Expected {len(candidates)} candidates for top_n=10, got {len(top10)}"
    )


def test_generate_recruiter_summary_structure_and_counts():
    """
    generate_recruiter_summary() must return correct counts for each
    status zone and include only Shortlisted and Review candidates in
    the top_candidates list.
    """
    candidates = apply_shortlisting(rank_candidates(make_candidate_pool()))
    summary = generate_recruiter_summary(candidates, job_id="JD-QE-001")

    # Top-level structure
    assert summary["job_id"] == "JD-QE-001", (
        f"Expected job_id='JD-QE-001', got '{summary['job_id']}'"
    )
    assert "summary" in summary
    assert "top_candidates" in summary

    # Counts (pool: 88.5 → Shortlisted, 76.0 → Shortlisted, 62.0 → Review,
    #          45.0 → Review, 30.0 → Rejected)
    s = summary["summary"]
    assert s["total_candidates"] == 5, (
        f"Expected total=5, got {s['total_candidates']}"
    )
    assert s["shortlisted"] == 2, (
        f"Expected shortlisted=2, got {s['shortlisted']}"
    )
    assert s["review"] == 1, (
        f"Expected review=1, got {s['review']}"
    )
    assert s["rejected"] == 2, (
        f"Expected rejected=2, got {s['rejected']}"
    )

    # top_candidates must exclude Rejected entries
    statuses = [c["status"] for c in summary["top_candidates"]]
    assert "Rejected" not in statuses, (
        f"Rejected candidates must not appear in top_candidates: {statuses}"
    )

    # Slim field check — no audit_trail or sub_scores
    for entry in summary["top_candidates"]:
        assert "audit_trail" not in entry, "audit_trail must be stripped from summary."
        assert "sub_scores" not in entry, "sub_scores must be stripped from summary."
        for key in ("candidate_id", "final_score", "match_label", "status", "rank"):
            assert key in entry, f"Missing expected key '{key}' in top_candidates entry."


def test_ranking_pipeline_returns_all_keys_and_sorted():
    """
    ranking_pipeline() must return a dict with exactly the three expected
    top-level keys, and ranked_list must be sorted descending by final_score.
    """
    candidates = make_candidate_pool()
    result = ranking_pipeline(candidates, job_id="JD-QE-002", top_n=3)

    # All three keys present
    assert "ranked_list" in result, "Expected 'ranked_list' key in pipeline output."
    assert "top_candidates" in result, "Expected 'top_candidates' key in pipeline output."
    assert "recruiter_summary" in result, "Expected 'recruiter_summary' key in pipeline output."

    # ranked_list must be sorted descending
    scores = [c["final_score"] for c in result["ranked_list"]]
    assert scores == sorted(scores, reverse=True), (
        f"Expected ranked_list sorted descending, got: {scores}"
    )

    # top_candidates honours top_n
    assert len(result["top_candidates"]) <= 3, (
        f"Expected at most 3 top candidates, got {len(result['top_candidates'])}"
    )

    # Every entry in ranked_list has both rank and status
    for candidate in result["ranked_list"]:
        assert "rank" in candidate, (
            f"Missing 'rank' on candidate {candidate.get('candidate_id')}"
        )
        assert "status" in candidate, (
            f"Missing 'status' on candidate {candidate.get('candidate_id')}"
        )