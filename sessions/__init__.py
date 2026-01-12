"""
Athena Server v2 - Session Management

This module provides centralized control over all Manus sessions.

Usage:
    from sessions import SessionType, create_managed_session

    result = await create_managed_session(
        session_type=SessionType.WORKSPACE_AGENDA,
        prompt="...",
        force=False
    )
"""

from sessions.manager import (
    SessionType,
    IdempotencyRule,
    SessionManager,
    create_managed_session,
    get_active_sessions,
    is_valid_session_type,
    get_registered_session_types,
)

__all__ = [
    "SessionType",
    "IdempotencyRule",
    "SessionManager",
    "create_managed_session",
    "get_active_sessions",
    "is_valid_session_type",
    "get_registered_session_types",
]
