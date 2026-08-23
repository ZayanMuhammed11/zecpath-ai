"""Role-based access control for governance_ai.

Fully isolated module: zero imports from any other project module.
"""

from __future__ import annotations

from governance_ai.governance_models import AccessRole, RolePermissions
from utils.logger import get_logger

logger = get_logger(__name__)


ROLE_REGISTRY: dict[AccessRole, RolePermissions] = {
    AccessRole.admin: RolePermissions(
        role=AccessRole.admin,
        allowed_actions=["read", "write", "delete"],
    ),
    AccessRole.recruiter: RolePermissions(
        role=AccessRole.recruiter,
        allowed_actions=["read", "write"],
    ),
    AccessRole.viewer: RolePermissions(
        role=AccessRole.viewer,
        allowed_actions=["read"],
    ),
}
"""Module-level constant mapping each AccessRole to its RolePermissions."""


def _validate_role(role: AccessRole) -> RolePermissions:
    """Look up a role in ROLE_REGISTRY or raise ValueError.

    Args:
        role: The AccessRole to look up.

    Returns:
        The RolePermissions registered for that role.

    Raises:
        ValueError: If `role` is not a recognized AccessRole present in
            ROLE_REGISTRY.
    """
    if role not in ROLE_REGISTRY:
        logger.error("Invalid AccessRole encountered: %r", role)
        raise ValueError(f"Invalid AccessRole: {role!r}")
    return ROLE_REGISTRY[role]


def has_access(role: AccessRole, action: str) -> bool:
    """Determine whether a role is permitted to perform an action.

    Args:
        role: The AccessRole attempting the action.
        action: The action name being attempted (e.g. "read", "write",
            "delete").

    Returns:
        True if `action` is in the role's allowed_actions, False
        otherwise.

    Raises:
        ValueError: If `role` is not a recognized AccessRole. This is
            treated as a caller bug, not a permission decision, and is
            never silently swallowed into a False return.
    """
    permissions = _validate_role(role)
    return action in permissions.allowed_actions


def get_role_permissions(role: AccessRole) -> RolePermissions:
    """Return the RolePermissions registered for a role.

    Args:
        role: The AccessRole to look up.

    Returns:
        The RolePermissions object for the given role.

    Raises:
        ValueError: If `role` is not a recognized AccessRole.
    """
    return _validate_role(role)
