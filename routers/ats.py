"""
Router handling ATS scoring and candidate shortlisting for Zecpath ATS API.
"""

import json
from datetime import datetime

from fastapi import APIRouter, HTTPException

from api.redis_client import get_redis
from api.request_models import ATSScoreRequest, ShortlistRequest
from api.response_models import (
    ATSScoreResponse,
    CandidateRankEntry,
    ShortlistResponse,
    SubScores,
)
from ats_engine.fairness_engine import apply_fairness_pipeline
from ats_engine.ranking_engine import ranking_pipeline
from scoring.ats_scorer import ATSScorer
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post("/score", response_model=ATSScoreResponse)
async def score_candidate(request: ATSScoreRequest) -> ATSScoreResponse:
    """
    Synchronously score a single candidate against a job profile using ATS logic.

    Expects:
    - A parsed candidate profile stored in Redis under
      'parsed_profile:{candidate_id}:{resume_id}'.
    - A job profile stored in Redis under 'job_profile:{job_id}'.

    Calls generate_candidate_score() and caches the result back to Redis.

    Args:
        request (ATSScoreRequest): Contains candidate_id, job_id, resume_id.

    Returns:
        ATSScoreResponse: Full ATS scoring breakdown for the candidate.

    Raises:
        HTTPException: 404 if parsed_profile or job_profile not found in Redis.
        HTTPException: 500 on scoring failure.
    """
    try:
        redis_conn = get_redis()

        parsed_key = f"parsed_profile:{request.candidate_id}:{request.resume_id}"
        job_key = f"job_profile:{request.job_id}"

        raw_parsed = redis_conn.get(parsed_key)
        if raw_parsed is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "status": "error",
                    "error_code": "NOT_FOUND",
                    "message": f"Parsed profile not found for key={parsed_key}",
                    "detail": None,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

        raw_job = redis_conn.get(job_key)
        if raw_job is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "status": "error",
                    "error_code": "NOT_FOUND",
                    "message": f"Job profile not found for key={job_key}",
                    "detail": None,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

        parsed_profile: dict = json.loads(raw_parsed)
        job_profile: dict = json.loads(raw_job)

        segmented_resume: dict = parsed_profile.get("segmented_resume", {})

        
        score_result: dict = ATSScorer.generate_candidate_score(
            parsed_profile,
            job_profile,
            segmented_resume,
            job_profile.get("jd_raw_text", ""),
        )

        score_key = f"ats_score:{request.candidate_id}:{request.job_id}"
        redis_conn.set(score_key, json.dumps(score_result))

        logger.info(
            "Scoring completed — candidate_id=%s, final_score=%.2f",
            request.candidate_id,
            score_result.get("final_score", 0.0),
        )

        raw_sub: dict = score_result.get("sub_scores", {})
        sub_scores = SubScores(
            skills=raw_sub.get("skills", 0.0),
            experience=raw_sub.get("experience", 0.0),
            education=raw_sub.get("education", 0.0),
            certifications=raw_sub.get("certifications", 0.0),
            semantic=raw_sub.get("semantic", 0.0),
            education_combined=raw_sub.get("education_combined", 0.0),
        )

        return ATSScoreResponse(
            status="success",
            timestamp=datetime.utcnow().isoformat(),
            candidate_id=request.candidate_id,
            job_id=request.job_id,
            final_score=score_result["final_score"],
            match_label=score_result["match_label"],
            shortlisted=score_result["shortlisted"],
            must_haves_met=score_result["must_haves_met"],
            sub_scores=sub_scores,
            weights_used=score_result["weights_used"],
            shortlist_threshold=score_result["shortlist_threshold"],
            job_title=score_result["job_title"],
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Scoring failed for candidate_id=%s: %s", request.candidate_id, exc
        )
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "error_code": "PROCESSING_ERR",
                "message": str(exc),
                "detail": None,
                "timestamp": datetime.utcnow().isoformat(),
            },
        ) from exc


@router.post("/shortlist", response_model=ShortlistResponse)
async def shortlist_candidates(request: ShortlistRequest) -> ShortlistResponse:
    """
    Rank and shortlist a batch of candidates for a given job.

    For each candidate_id, fetches their ATS score from Redis, then passes
    the full list through ranking_pipeline() and apply_fairness_pipeline().

    Candidates without a cached score are skipped with a WARNING log.

    Args:
        request (ShortlistRequest): job_id, list of candidate_ids, optional threshold.

    Returns:
        ShortlistResponse: Ranked list with fairness scores and recruiter summary.

    Raises:
        HTTPException: 500 on pipeline failure.
    """
    try:
        redis_conn = get_redis()
        score_dicts: list[dict] = []

        for candidate_id in request.candidate_ids:
            score_key = f"ats_score:{candidate_id}:{request.job_id}"
            raw_score = redis_conn.get(score_key)

            if raw_score is None:
                logger.warning(
                    "ATS score not found — skipping candidate_id=%s, job_id=%s",
                    candidate_id,
                    request.job_id,
                )
                continue

            score_data: dict = json.loads(raw_score)
            score_data["candidate_id"] = candidate_id
            score_dicts.append(score_data)

        ranked_list, top_candidates, recruiter_summary = ranking_pipeline(score_dicts)

        ranked_list = apply_fairness_pipeline(ranked_list)

        shortlisted_count = sum(1 for c in ranked_list if c.get("zone") == "shortlist")
        review_count = sum(1 for c in ranked_list if c.get("zone") == "review")
        rejected_count = sum(1 for c in ranked_list if c.get("zone") == "rejected")

        logger.info(
            "Shortlisting complete — job_id=%s, total=%d, shortlisted=%d, review=%d, rejected=%d",
            request.job_id,
            len(ranked_list),
            shortlisted_count,
            review_count,
            rejected_count,
        )

        entries: list[CandidateRankEntry] = [
            CandidateRankEntry(
                candidate_id=c["candidate_id"],
                rank=c["rank"],
                final_score=c["final_score"],
                fair_score=c["fair_score"],
                zone=c["zone"],
                bias_report=c.get("bias_report", {}),
            )
            for c in ranked_list
        ]

        return ShortlistResponse(
            status="success",
            timestamp=datetime.utcnow().isoformat(),
            job_id=request.job_id,
            total_candidates=len(ranked_list),
            shortlisted_count=shortlisted_count,
            review_count=review_count,
            rejected_count=rejected_count,
            ranked_list=entries,
            recruiter_summary=recruiter_summary,
        )

    except Exception as exc:
        logger.error("Shortlisting failed for job_id=%s: %s", request.job_id, exc)
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "error_code": "PROCESSING_ERR",
                "message": str(exc),
                "detail": None,
                "timestamp": datetime.utcnow().isoformat(),
            },
        ) from exc