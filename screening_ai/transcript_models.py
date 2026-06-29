"""
Pydantic v2 models for AI screening call transcripts.

This module defines the data structures used to capture and represent
screening call conversations between candidates and the AI interviewer.
It sits between the question bank (Day 22) and the answer understanding
engine (Day 25).

Redis key pattern: transcript:{candidate_id}:{job_id}
"""

from __future__ import annotations

from enum import Enum
from typing import List

from pydantic import BaseModel, Field


class TranscriptStatus(str, Enum):
    """Lifecycle states for a screening transcript."""

    in_progress = "in_progress"
    completed = "completed"
    abandoned = "abandoned"


class AnswerQuality(str, Enum):
    """Quality classification of a candidate's answer to a screening question."""

    good = "good"
    basic = "basic"
    too_short = "too_short"
    off_topic = "off_topic"
    no_answer = "no_answer"


class TranscriptEntry(BaseModel):
    """
    Represents a single question-answer exchange in a screening call.

    The question_text is stored directly in every entry so the transcript
    is fully self-contained — no secondary Redis lookup is required when
    reading or replaying entries later.

    Attributes:
        question_id: Unique identifier of the question from the question bank.
        question_text: Full question text captured at the time of asking.
        answer_text: Normalized candidate answer (post-STT cleanup).
        answer_quality: Quality classification determined after normalization.
        confidence_score: Speech-to-text confidence score, range 0.0–1.0.
        keywords_detected: Domain keywords found in the normalized answer.
        follow_up_triggered: Whether a follow-up question was issued.
        follow_up_question: Text of the follow-up question (if triggered).
        follow_up_answer: Candidate's answer to the follow-up (if triggered).
        start_time: Exchange start timestamp in HH:MM:SS format.
        end_time: Exchange end timestamp in HH:MM:SS format.
        duration_seconds: Duration of this exchange in seconds (>= 0).
    """

    question_id: str
    question_text: str
    answer_text: str
    answer_quality: AnswerQuality = AnswerQuality.good
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)
    keywords_detected: List[str] = Field(default_factory=list)
    follow_up_triggered: bool = False
    follow_up_question: str = ""
    follow_up_answer: str = ""
    start_time: str = ""
    end_time: str = ""
    duration_seconds: int = Field(default=0, ge=0)


class ScreeningTranscript(BaseModel):
    """
    Full transcript of a candidate's AI screening call for a given job.

    Aggregates all TranscriptEntry objects from a single session and
    tracks computed metrics (overall STT confidence, total duration).
    Metrics are never stored manually — they are always recomputed from
    entries to ensure accuracy.

    Attributes:
        transcript_id: Unique ID in format ``TRX-{candidate_id}-{job_id}``.
        candidate_id: Identifier of the candidate being screened.
        job_id: Identifier of the job role being screened for.
        language: BCP-47 language code for the call (default: ``"en"``).
        status: Current lifecycle status of the transcript.
        entries: Ordered list of question-answer exchanges.
        overall_confidence: Average STT confidence across all entries.
        total_questions_asked: Count of questions asked in this session.
        total_duration_seconds: Cumulative call duration across all entries.
        created_at: ISO-8601 UTC timestamp when the transcript was created.
        completed_at: ISO-8601 UTC timestamp when the transcript was completed.
        screening_round: Label for the screening stage (default: ``"HR Screening"``).
        notes: Free-text notes added by the system or a human reviewer.
    """

    transcript_id: str
    candidate_id: str
    job_id: str
    language: str = "en"
    status: TranscriptStatus = TranscriptStatus.in_progress
    entries: List[TranscriptEntry] = Field(default_factory=list)
    overall_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    total_questions_asked: int = 0
    total_duration_seconds: int = 0
    created_at: str
    completed_at: str = ""
    screening_round: str = "HR Screening"
    notes: str = ""

    def compute_overall_confidence(self) -> float:
        """
        Compute the average STT confidence score across all transcript entries.

        Returns:
            Mean confidence value in range 0.0–1.0, or 0.0 if no entries exist.
        """
        if not self.entries:
            return 0.0
        return sum(e.confidence_score for e in self.entries) / len(self.entries)

    def compute_total_duration(self) -> int:
        """
        Compute total call duration by summing every entry's duration.

        Returns:
            Total duration in seconds.
        """
        return sum(e.duration_seconds for e in self.entries)
