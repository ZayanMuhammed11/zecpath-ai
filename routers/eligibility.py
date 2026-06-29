"""
Router handling eligibility evaluation for the Zecpath Eligibility Decision Engine.
"""

import json
from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.redis_client import get_redis
from screening_ai.eligibility_engine import EligibilityEngine
from screening_ai.eligibility_models import EligibilityResult
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ── Request models ─────────────────────────────────────────────────────────────

class EvaluateRequest(BaseModel):
    """Request body for single eligibility evaluation."""

    candidate_id: str
    job_id: str


class BatchEvaluateRequest(BaseModel):
    """Request body for batch eligibility evaluation."""

    pairs: List[EvaluateRequest]


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("/evaluate", response_model=EligibilityResult)
async def evaluate_eligibility(request: EvaluateRequest) -> EligibilityResult:
    """
    Evaluate eligibility for a single candidate against a specific job.

    Reads the ATS score and parsed profile from Redis (Sprint 1 keys),
    applies job-specific eligibility rules, writes result to Redis, and returns it.

    Args:
        request (EvaluateRequest): Contains candidate_id and job_id.

    Returns:
        EligibilityResult: Full eligibility breakdown with status and checks.

    Raises:
        HTTPException: 404 if ATS score or parsed profile not found in Redis.
        HTTPException: 500 on unexpected error.
    """
    try:
        r = get_redis()
        engine = EligibilityEngine(r)
        result = engine.evaluate(request.candidate_id, request.job_id)

        if result is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "status": "error",
                    "error_code": "NOT_FOUND",
                    "message": (
                        f"ATS score or parsed profile not found for "
                        f"candidate_id={request.candidate_id}, job_id={request.job_id}"
                    ),
                    "detail": None,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

        logger.info(
            "Eligibility endpoint — candidate_id=%s, job_id=%s, status=%s",
            request.candidate_id,
            request.job_id,
            result.eligibility_status,
        )

        return result

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Eligibility evaluation failed — candidate_id=%s: %s",
            request.candidate_id,
            exc,
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


@router.post("/evaluate-batch", response_model=List[EligibilityResult])
async def evaluate_eligibility_batch(
    request: BatchEvaluateRequest,
) -> List[EligibilityResult]:
    """
    Evaluate eligibility for a batch of candidate/job pairs.

    Pairs with missing Redis data are silently skipped (engine returns None).

    Args:
        request (BatchEvaluateRequest): List of candidate_id/job_id pairs.

    Returns:
        List[EligibilityResult]: Results for all successfully evaluated pairs.

    Raises:
        HTTPException: 500 on unexpected error.
    """
    try:
        r = get_redis()
        engine = EligibilityEngine(r)

        pairs = [(p.candidate_id, p.job_id) for p in request.pairs]
        results = engine.evaluate_batch(pairs)

        logger.info(
            "Batch eligibility complete — total_pairs=%d, evaluated=%d",
            len(pairs),
            len(results),
        )

        return results

    except Exception as exc:
        logger.error("Batch eligibility evaluation failed: %s", exc)
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


@router.get("/result/{candidate_id}/{job_id}", response_model=EligibilityResult)
async def get_eligibility_result(candidate_id: str, job_id: str) -> EligibilityResult:
    """
    Retrieve a previously computed eligibility result from Redis.

    Reads eligibility:{candidate_id}:{job_id} directly — does not re-evaluate.

    Args:
        candidate_id: The candidate identifier.
        job_id: The job identifier.

    Returns:
        EligibilityResult: The stored eligibility result.

    Raises:
        HTTPException: 404 if no result found in Redis.
        HTTPException: 500 on unexpected error.
    """
    try:
        r = get_redis()
        key = f"eligibility:{candidate_id}:{job_id}"
        raw = r.get(key)

        if raw is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "status": "error",
                    "error_code": "NOT_FOUND",
                    "message": f"No eligibility result found for key={key}",
                    "detail": None,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

        return EligibilityResult(**json.loads(raw))

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Failed to fetch eligibility result — candidate_id=%s, job_id=%s: %s",
            candidate_id,
            job_id,
            exc,
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