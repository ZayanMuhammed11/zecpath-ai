"""
Router handling synchronous candidate screening runs for the Zecpath
Screening Pipeline.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from screening_ai.screening_pipeline import run_screening_pipeline
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ── Request models ─────────────────────────────────────────────────────────────

class QAPairInput(BaseModel):
    """One question/answer exchange supplied directly by the caller.

    LIMITATION: this does not look up the Day 22 question_bank:{job_id}
    Redis key. The caller must supply expected_keywords and
    expected_intent directly per question. Wiring in the real question
    bank lookup is future scope.
    """

    question_id: str
    audio_text: str
    confidence: float
    expected_keywords: Optional[list[str]] = None
    expected_intent: Optional[str] = None


class ScreeningRunRequest(BaseModel):
    """Request body for running a full candidate screening synchronously."""

    candidate_id: str
    job_id: str
    qa_pairs: list[QAPairInput]


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("/run")
async def run_screening(request: ScreeningRunRequest) -> dict:
    """
    Run a candidate's screening Q&A through the full pipeline synchronously.

    KEY DECISION: kept synchronous, not async/Redis-Queue, because this
    operates on already-simulated text answers (milliseconds of
    processing), not a real voice call (which would take minutes and
    require the async Queue+Webhook pattern documented in the system
    architecture). If real STT/voice integration replaces the simulation
    layer in production, this endpoint should be converted to the async
    pattern at that time.

    Args:
        request: candidate_id, job_id, and the full list of qa_pairs.

    Returns:
        The full screening report dict produced by run_screening_pipeline().

    Raises:
        HTTPException: 500 on any pipeline failure.
    """
    try:
        qa_dicts = [qa.model_dump() for qa in request.qa_pairs]
        report = run_screening_pipeline(
            request.candidate_id, request.job_id, qa_dicts
        )
        logger.info(
            "Screening run complete — candidate_id=%s job_id=%s decision=%s",
            request.candidate_id,
            request.job_id,
            report.get("decision"),
        )
        return report
    except Exception as exc:
        logger.error(
            "Screening run failed — candidate_id=%s job_id=%s: %s",
            request.candidate_id,
            request.job_id,
            exc,
        )
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "error_code": "PROCESSING_ERR",
                "message": str(exc),
                "detail": None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        ) from exc
