"""
Pydantic v2 response models for Zecpath ATS API endpoints.
All response models inherit from BaseResponse.
"""

from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from utils.logger import get_logger

logger = get_logger(__name__)


class BaseResponse(BaseModel):
    """
    Base response model providing status and timestamp fields
    for all API responses.
    """

    status: str
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )


class ResumeUploadResponse(BaseResponse):
    """
    Response returned after a resume file is successfully uploaded.
    """

    resume_id: str
    candidate_id: str
    job_id: str
    message: str


class JobSubmittedResponse(BaseResponse):
    """
    Response returned when a background RQ job has been enqueued successfully.
    """

    job_id: str
    message: str


class JobStatusResponse(BaseResponse):
    """
    Response returned when polling the status of an RQ background job.
    """

    job_id: str
    job_status: str  # queued / started / finished / failed
    result: Optional[dict] = None


class SubScores(BaseModel):
    """
    Breakdown of individual ATS scoring dimensions for a candidate.
    """

    skills: float
    experience: float
    education: float
    certifications: float
    semantic: float
    education_combined: float


class ATSScoreResponse(BaseResponse):
    """
    Full ATS scoring result for a single candidate against a job profile.
    """

    candidate_id: str
    job_id: str
    final_score: float
    match_label: str
    shortlisted: bool
    must_haves_met: bool
    sub_scores: SubScores
    weights_used: dict
    shortlist_threshold: float
    job_title: str


class CandidateRankEntry(BaseModel):
    """
    A single candidate's entry in the ranked shortlist output,
    including fairness-adjusted scores and bias report.
    """

    candidate_id: str
    rank: int
    final_score: float
    fair_score: float
    zone: str  # shortlist / review / rejected
    bias_report: dict


class ShortlistResponse(BaseResponse):
    """
    Aggregated shortlisting result for all candidates evaluated for a job.
    """

    job_id: str
    total_candidates: int
    shortlisted_count: int
    review_count: int
    rejected_count: int
    ranked_list: List[CandidateRankEntry]
    recruiter_summary: dict


class ErrorResponse(BaseResponse):
    """
    Standardised error response structure for all handled API exceptions.
    """

    error_code: str
    message: str
    detail: Optional[str] = None