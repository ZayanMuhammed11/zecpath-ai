"""Audit log entry shaping for governance_ai.

Fully isolated module: zero imports from any other project module.
"""

from __future__ import annotations

from datetime import datetime, timezone

from governance_ai.governance_models import AuditLogEntry
from utils.logger import get_logger

logger = get_logger(__name__)


def log_event(event_type: str, candidate_id: str, data: dict) -> AuditLogEntry:
    """Build a single AuditLogEntry. Does not persist it anywhere.

    This is a pure, deterministic function (aside from the current
    timestamp): given the same inputs at the same instant, it returns an
    equivalent AuditLogEntry. It performs no I/O — no file write, no
    database write, no Redis write. Persistence of audit log entries is
    explicitly out of scope for this module; no audit-log storage or
    retrieval layer exists in this codebase yet. Callers are responsible
    for persisting the returned entry wherever that storage layer is
    eventually implemented.

    Args:
        event_type: A short machine-readable label for the event.
        candidate_id: The identifier of the candidate the event concerns.
        data: Arbitrary event-specific payload.

    Returns:
        A fully populated AuditLogEntry with timestamp set to
        datetime.now(timezone.utc).isoformat().
    """
    entry = AuditLogEntry(
        event_type=event_type,
        candidate_id=candidate_id,
        data=data,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    logger.info(
        "Shaped audit log entry (unpersisted): event_type=%s candidate_id=%s",
        event_type,
        candidate_id,
    )
    return entry
