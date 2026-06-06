"""
Router handling resume upload and parse-job enqueueing for Zecpath ATS API.
"""

import os
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Form, HTTPException, UploadFile
from rq import Queue

from api.redis_client import get_redis
from api.request_models import ResumeParseRequest
from api.response_models import JobSubmittedResponse, ResumeUploadResponse
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()

UPLOAD_DIR = os.path.join("data", "uploads")

q = Queue("ats_queue", connection=get_redis())


@router.post("/upload", response_model=ResumeUploadResponse)
async def upload_resume(
    file: UploadFile,
    job_id: str = Form(...),
    candidate_id: str = Form(...),
) -> ResumeUploadResponse:
    """
    Accept a PDF resume via multipart upload alongside job_id and candidate_id
    form fields. Saves the file to disk and returns a generated resume_id.

    Args:
        file (UploadFile): The resume PDF uploaded by the client.
        job_id (str): The job the candidate is applying for.
        candidate_id (str): Unique identifier for the candidate.

    Returns:
        ResumeUploadResponse: Contains the generated resume_id and metadata.

    Raises:
        HTTPException: 500 if file saving fails for any reason.
    """
    try:
        os.makedirs(UPLOAD_DIR, exist_ok=True)

        resume_id = f"R-{candidate_id}-{uuid4().hex[:8].upper()}"
        filename = f"{candidate_id}_{resume_id}.pdf"
        file_path = os.path.join(UPLOAD_DIR, filename)

        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)

        logger.info(
            "Resume uploaded — resume_id=%s, candidate_id=%s, path=%s",
            resume_id,
            candidate_id,
            file_path,
        )

        return ResumeUploadResponse(
            status="success",
            timestamp=datetime.utcnow().isoformat(),
            resume_id=resume_id,
            candidate_id=candidate_id,
            job_id=job_id,
            message=f"Resume uploaded successfully as {filename}",
        )

    except Exception as exc:
        logger.error("Resume upload failed for candidate_id=%s: %s", candidate_id, exc)
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


@router.post("/parse", response_model=JobSubmittedResponse)
async def enqueue_parse_resume(request: ResumeParseRequest) -> JobSubmittedResponse:
    """
    Enqueue an asynchronous resume-parse job to the RQ 'ats_queue'.
    The actual parsing is performed by worker.task_handlers.handle_parse_resume.

    Args:
        request (ResumeParseRequest): Contains resume_id, candidate_id, job_id.

    Returns:
        JobSubmittedResponse: Contains the RQ job.id for status polling.

    Raises:
        HTTPException: 404 if no resume file matching resume_id is found.
        HTTPException: 500 if enqueueing fails.
    """
    try:
        # Locate resume file matching the resume_id prefix
        resume_path: str | None = None
        if os.path.isdir(UPLOAD_DIR):
            for fname in os.listdir(UPLOAD_DIR):
                if request.resume_id in fname:
                    resume_path = os.path.join(UPLOAD_DIR, fname)
                    break

        if resume_path is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "status": "error",
                    "error_code": "NOT_FOUND",
                    "message": f"No resume file found for resume_id={request.resume_id}",
                    "detail": None,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

        job = q.enqueue(
            "worker.task_handlers.handle_parse_resume",
            resume_path,
            request.candidate_id,
            request.job_id,
            request.resume_id,
        )

        logger.info(
            "Parse job enqueued — rq_job_id=%s, candidate_id=%s",
            job.id,
            request.candidate_id,
        )

        return JobSubmittedResponse(
            status="queued",
            timestamp=datetime.utcnow().isoformat(),
            job_id=job.id,
            message=f"Parse job enqueued for candidate {request.candidate_id}",
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Failed to enqueue parse job for candidate_id=%s: %s",
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