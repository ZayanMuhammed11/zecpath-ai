"""
Pydantic v2 request models for Zecpath ATS API endpoints.
"""

from typing import List, Optional
from pydantic import BaseModel
from utils.logger import get_logger

logger = get_logger(__name__)


class ResumeUploadRequest(BaseModel):
    """
    Request model for resume upload endpoint.
    Note: The actual file is received as multipart form data separately.
    """

    job_id: str
    candidate_id: str


class ResumeParseRequest(BaseModel):
    """
    Request model for enqueuing a resume parse job.
    """

    resume_id: str
    candidate_id: str
    job_id: str


class ATSScoreRequest(BaseModel):
    """
    Request model for synchronous ATS scoring of a single candidate.
    Requires that parsing has already been completed and stored in Redis.
    """

    candidate_id: str
    job_id: str
    resume_id: str


class ShortlistRequest(BaseModel):
    """
    Request model for batch shortlisting and ranking of candidates for a job.
    """

    job_id: str
    candidate_ids: List[str]
    shortlist_threshold: Optional[float] = 75.0