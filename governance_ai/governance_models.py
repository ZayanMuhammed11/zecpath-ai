"""Data shapes for governance_ai.

This module defines pure data models only. It contains no business logic,
no persistence, no encryption, and no consent-capture flow. It is fully
isolated from every other project module (decision_ai, interview_ai,
screening_ai, ats_engine, scoring, technical_ai, machine_test_ai,
visual_behavior_ai, integrity_ai, final_decision_ai, hiring_report_ai) and
must remain so.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel

from utils.logger import get_logger

logger = get_logger(__name__)


class AccessRole(str, Enum):
    """Role-based access control role.

    Deliberately distinct from any candidate-seniority "RoleLevel" concept
    that may exist elsewhere in the platform. There is no import
    relationship, and none should ever be introduced, between AccessRole
    (an RBAC concept for platform users) and any candidate-seniority
    concept named RoleLevel (a concept about candidates). They must never
    be confused.
    """

    admin = "admin"
    recruiter = "recruiter"
    viewer = "viewer"


class RolePermissions(BaseModel):
    """The set of actions a given AccessRole is permitted to perform.

    Attributes:
        role: The AccessRole this permission set applies to.
        allowed_actions: List of action names (e.g. "read", "write",
            "delete") permitted for this role.
    """

    role: AccessRole
    allowed_actions: list[str]


class AuditLogEntry(BaseModel):
    """A single, shaped audit log record.

    This model describes the SHAPE of an audit log entry only. Nothing in
    this module writes an AuditLogEntry anywhere (no file, no database, no
    Redis). Persistence is out of scope and must be implemented, if ever,
    by a separate storage layer outside governance_ai.

    Attributes:
        event_type: A short machine-readable label for the event
            (e.g. "candidate_viewed", "decision_overridden").
        candidate_id: The identifier of the candidate the event concerns.
        data: Arbitrary event-specific payload.
        timestamp: ISO-8601 timestamp string produced by
            datetime.now(timezone.utc).isoformat().
    """

    event_type: str
    candidate_id: str
    data: dict
    timestamp: str


class ConsentRecord(BaseModel):
    """The SHAPE of a future consent record only.

    IMPORTANT: This model defines a data shape only. No consent-capture
    flow, UI, storage, or enforcement logic exists anywhere in this
    module or (to this module's knowledge) elsewhere in the codebase.
    Defining this model does NOT resolve the platform's still-open
    consent implementation gap; it only gives future code a shared shape
    to target once that gap is addressed.

    Attributes:
        candidate_id: The identifier of the candidate the consent
            concerns.
        consent_type: A free-form string describing what the consent is
            for (e.g. "ai_interview", "recording", "data_processing").
            Deliberately not an enum because the real, final set of
            consent types has not yet been decided.
        granted: Whether consent was granted (True) or denied/withdrawn
            (False).
        timestamp: ISO-8601 timestamp string associated with the consent
            decision.
    """

    candidate_id: str
    consent_type: str
    granted: bool
    timestamp: str


class RetentionPolicy(BaseModel):
    """The SHAPE of a data-retention policy, with no default retention period.

    IMPORTANT: retention_days is caller-supplied only. This model must
    never hardcode or default to any specific number of retention days.
    The exact retention window for any data_type is a business/legal
    decision that is explicitly out of scope for this module and this
    engineering task. When retention_days is not provided, it is None —
    callers must supply a real value from an authoritative source before
    this policy can be considered actionable.

    Attributes:
        data_type: A label identifying what kind of data this policy
            applies to (e.g. "interview_recording", "resume").
        retention_days: Caller-supplied number of days to retain the
            data, or None if not yet determined. No default value is
            ever substituted by this module.
    """

    data_type: str
    retention_days: Optional[int] = None
