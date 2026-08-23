"""Tests for governance_ai.

Deterministic pytest tests — no use of the `random` module.
"""

from __future__ import annotations

import inspect
from datetime import datetime

import pytest

from governance_ai import access_control, audit_log, governance_models
from governance_ai.access_control import (
    ROLE_REGISTRY,
    get_role_permissions,
    has_access,
)
from governance_ai.audit_log import log_event
from governance_ai.governance_models import (
    AccessRole,
    AuditLogEntry,
    ConsentRecord,
    RetentionPolicy,
    RolePermissions,
)


# ---------------------------------------------------------------------------
# has_access
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "role,action,expected",
    [
        (AccessRole.admin, "read", True),
        (AccessRole.admin, "write", True),
        (AccessRole.admin, "delete", True),
        (AccessRole.recruiter, "read", True),
        (AccessRole.recruiter, "write", True),
        (AccessRole.recruiter, "delete", False),
        (AccessRole.viewer, "read", True),
        (AccessRole.viewer, "write", False),
        (AccessRole.viewer, "delete", False),
    ],
)
def test_has_access_matches_role_registry(role, action, expected):
    """has_access() should reflect exactly what ROLE_REGISTRY defines."""
    assert has_access(role, action) is expected


def test_has_access_raises_for_invalid_role():
    """An unrecognized role must raise ValueError, not return False."""
    with pytest.raises(ValueError, match="Invalid AccessRole"):
        has_access("superuser", "read")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# get_role_permissions
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "role,expected_actions",
    [
        (AccessRole.admin, ["read", "write", "delete"]),
        (AccessRole.recruiter, ["read", "write"]),
        (AccessRole.viewer, ["read"]),
    ],
)
def test_get_role_permissions_returns_correct_permissions(role, expected_actions):
    perms = get_role_permissions(role)
    assert isinstance(perms, RolePermissions)
    assert perms.role == role
    assert perms.allowed_actions == expected_actions


def test_get_role_permissions_raises_for_invalid_role():
    with pytest.raises(ValueError, match="Invalid AccessRole"):
        get_role_permissions("nope")  # type: ignore[arg-type]


def test_role_registry_has_exactly_three_roles():
    assert set(ROLE_REGISTRY.keys()) == {
        AccessRole.admin,
        AccessRole.recruiter,
        AccessRole.viewer,
    }


# ---------------------------------------------------------------------------
# log_event
# ---------------------------------------------------------------------------


def test_log_event_returns_audit_log_entry_with_exact_fields():
    payload = {"reason": "manual_override", "score": 87}
    entry = log_event(
        event_type="decision_overridden",
        candidate_id="cand-123",
        data=payload,
    )

    assert isinstance(entry, AuditLogEntry)
    assert entry.event_type == "decision_overridden"
    assert entry.candidate_id == "cand-123"
    assert entry.data == payload


def test_log_event_timestamp_is_valid_iso8601():
    entry = log_event(event_type="candidate_viewed", candidate_id="cand-1", data={})
    # Should not raise — confirms genuine ISO-8601 format.
    parsed = datetime.fromisoformat(entry.timestamp)
    assert parsed.tzinfo is not None


# ---------------------------------------------------------------------------
# ConsentRecord / RetentionPolicy construction
# ---------------------------------------------------------------------------


def test_consent_record_can_be_constructed_with_valid_data():
    record = ConsentRecord(
        candidate_id="cand-1",
        consent_type="ai_interview",
        granted=True,
        timestamp=datetime.now().isoformat(),
    )
    assert record.candidate_id == "cand-1"
    assert record.consent_type == "ai_interview"
    assert record.granted is True


def test_retention_policy_can_be_constructed_with_explicit_days():
    policy = RetentionPolicy(data_type="interview_recording", retention_days=30)
    assert policy.data_type == "interview_recording"
    assert policy.retention_days == 30


def test_retention_policy_retention_days_defaults_to_none_not_a_hardcoded_value():
    policy = RetentionPolicy(data_type="resume")
    # Explicitly assert genuine None — not some silently substituted number.
    assert policy.retention_days is None


# ---------------------------------------------------------------------------
# Static source scan: no `random` usage anywhere in governance_ai
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "module",
    [governance_models, access_control, audit_log],
)
def test_no_random_module_usage(module):
    """Static scan confirming no module in governance_ai imports `random`."""
    source = inspect.getsource(module)
    assert "import random" not in source
    assert "from random" not in source
