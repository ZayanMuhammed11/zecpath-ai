"""
Router for polling the status of background RQ jobs in Zecpath ATS API.
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException
from rq.job import Job
from rq.exceptions import NoSuchJobError

from api.redis_client import get_redis_binary
from api.response_models import JobStatusResponse
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()

_RQ_STATUS_MAP: dict[str, str] = {
    "queued": "queued",
    "started": "started",
    "finished": "finished",
    "failed": "failed",
    "deferred": "queued",
    "scheduled": "queued",
    "stopped": "failed",
    "canceled": "failed",
}


@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str) -> JobStatusResponse:
    """
    Fetch the current status of an RQ background job by its job ID.

    Maps RQ's internal status strings to one of:
    queued / started / finished / failed.

    If the job has finished, the result payload is included.
    If the job has failed, the exception traceback is included as the result.

    Args:
        job_id (str): The RQ job ID returned at enqueueing time.

    Returns:
        JobStatusResponse: Current status and optional result or error detail.

    Raises:
        HTTPException: 404 if no job with the given ID exists in Redis.
        HTTPException: 500 on unexpected errors.
    """
    try:
        redis_conn = get_redis_binary()  # Use binary connection for RQ Job fetching
        job = Job.fetch(job_id, connection=redis_conn)

        raw_status: str = job.get_status().value  # RQ >= 1.10 returns JobStatus enum
        mapped_status: str = _RQ_STATUS_MAP.get(raw_status, "failed")

        result: dict | None = None

        if mapped_status == "finished":
            result = job.result if isinstance(job.result, dict) else {"output": str(job.result)}
        elif mapped_status == "failed":
            result = {"error": job.exc_info or "Unknown failure"}

        logger.info("Job status polled — job_id=%s, status=%s", job_id, mapped_status)

        return JobStatusResponse(
            status="success",
            timestamp=datetime.utcnow().isoformat(),
            job_id=job_id,
            job_status=mapped_status,
            result=result,
        )

    except NoSuchJobError:
        logger.warning("Job not found — job_id=%s", job_id)
        raise HTTPException(
            status_code=404,
            detail={
                "status": "error",
                "error_code": "NOT_FOUND",
                "message": f"No job found with id={job_id}",
                "detail": None,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )
    except Exception as exc:
        logger.error("Failed to fetch job status for job_id=%s: %s", job_id, exc)
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