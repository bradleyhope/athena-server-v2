"""
Athena Brain - State Layer (Layer 3)

Context windows, pending actions, and session state.
"""

import logging
import json
from typing import Optional, List, Dict, Any
from datetime import datetime, date

from db.neon import db_cursor

logger = logging.getLogger("athena.db.brain.state")


# =============================================================================
# CONTEXT WINDOWS
# =============================================================================

def get_context_window(session_id: str, context_type: str = None) -> List[Dict]:
    """Get context windows for a session."""
    with db_cursor() as cursor:
        query = """
            SELECT * FROM context_windows
            WHERE session_id = %s
            AND (expires_at IS NULL OR expires_at > NOW())
        """
        params = [session_id]

        if context_type:
            query += " AND context_type = %s"
            params.append(context_type)

        query += " ORDER BY priority DESC, created_at DESC"
        cursor.execute(query, params)
        return cursor.fetchall()


def set_context_window(
    session_id: str,
    context_type: str,
    context_data: Dict,
    priority: int = 0,
    expires_at: datetime = None
) -> str:
    """Create or update a context window."""
    with db_cursor() as cursor:
        cursor.execute("""
            INSERT INTO context_windows (session_id, context_type, context_data, priority, expires_at)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (session_id, context_type, json.dumps(context_data), priority, expires_at))
        return str(cursor.fetchone()['id'])


def clear_context_windows(session_id: str) -> int:
    """Clear all context windows for a session."""
    with db_cursor() as cursor:
        cursor.execute("DELETE FROM context_windows WHERE session_id = %s", (session_id,))
        return cursor.rowcount


# =============================================================================
# PENDING ACTIONS
# =============================================================================

def get_pending_actions(status: str = 'pending', priority: str = None) -> List[Dict]:
    """Get pending actions."""
    with db_cursor() as cursor:
        query = "SELECT * FROM pending_actions WHERE status = %s"
        params = [status]

        if priority:
            query += " AND priority = %s"
            params.append(priority)

        query += " ORDER BY CASE priority WHEN 'urgent' THEN 1 WHEN 'high' THEN 2 WHEN 'normal' THEN 3 ELSE 4 END, created_at"
        cursor.execute(query, params)
        return cursor.fetchall()


def create_pending_action(
    action_type: str,
    action_data: Dict,
    priority: str = 'normal',
    requires_approval: bool = True,
    source_workflow_id: str = None,
    source_synthesis_id: str = None,
    expires_at: datetime = None
) -> str:
    """Create a pending action."""
    with db_cursor() as cursor:
        cursor.execute("""
            INSERT INTO pending_actions (
                action_type, action_data, priority, requires_approval,
                source_workflow_id, source_synthesis_id, expires_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            action_type, json.dumps(action_data), priority, requires_approval,
            source_workflow_id, source_synthesis_id, expires_at
        ))
        return str(cursor.fetchone()['id'])


def approve_pending_action(action_id: str, approved_by: str, reason: str = None) -> bool:
    """Approve a pending action."""
    with db_cursor() as cursor:
        cursor.execute("""
            UPDATE pending_actions SET
                status = 'approved',
                approved_by = %s,
                approval_reason = %s,
                approved_at = NOW()
            WHERE id = %s AND status = 'pending'
        """, (approved_by, reason, action_id))
        return cursor.rowcount > 0


def reject_pending_action(action_id: str, approved_by: str, reason: str = None) -> bool:
    """Reject a pending action."""
    with db_cursor() as cursor:
        cursor.execute("""
            UPDATE pending_actions SET
                status = 'rejected',
                approved_by = %s,
                approval_reason = %s,
                approved_at = NOW()
            WHERE id = %s AND status = 'pending'
        """, (approved_by, reason, action_id))
        return cursor.rowcount > 0


def execute_pending_action(action_id: str, result: Dict = None) -> bool:
    """Mark a pending action as executed."""
    with db_cursor() as cursor:
        cursor.execute("""
            UPDATE pending_actions SET
                status = 'executed',
                executed_at = NOW(),
                result = %s
            WHERE id = %s AND status = 'approved'
        """, (json.dumps(result) if result else None, action_id))
        return cursor.rowcount > 0


# =============================================================================
# SESSION STATE
# =============================================================================

def get_session_state(session_type: str, session_date: date = None) -> Optional[Dict]:
    """Get session state."""
    with db_cursor() as cursor:
        if session_date:
            cursor.execute("""
                SELECT * FROM session_state
                WHERE session_type = %s AND session_date = %s
            """, (session_type, session_date))
        else:
            cursor.execute("""
                SELECT * FROM session_state
                WHERE session_type = %s
                ORDER BY session_date DESC LIMIT 1
            """, (session_type,))
        return cursor.fetchone()


def set_session_state(
    session_type: str,
    session_date: date,
    manus_task_id: str = None,
    manus_task_url: str = None,
    state_data: Dict = None,
    handoff_context: Dict = None
) -> str:
    """Create or update session state."""
    with db_cursor() as cursor:
        cursor.execute("""
            INSERT INTO session_state (session_type, session_date, manus_task_id, manus_task_url, state_data, handoff_context)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (session_type, session_date) DO UPDATE SET
                manus_task_id = COALESCE(EXCLUDED.manus_task_id, session_state.manus_task_id),
                manus_task_url = COALESCE(EXCLUDED.manus_task_url, session_state.manus_task_url),
                state_data = COALESCE(EXCLUDED.state_data, session_state.state_data),
                handoff_context = COALESCE(EXCLUDED.handoff_context, session_state.handoff_context),
                updated_at = NOW()
            RETURNING id
        """, (
            session_type, session_date, manus_task_id, manus_task_url,
            json.dumps(state_data) if state_data else None,
            json.dumps(handoff_context) if handoff_context else None
        ))
        return str(cursor.fetchone()['id'])


def update_session_state(
    session_type: str,
    handoff_context: Dict = None,
    state_data: Dict = None,
    key_learnings: list = None
) -> bool:
    """
    Update session state for the current date.

    Args:
        session_type: Type of session
        handoff_context: Context to pass to next session
        state_data: Current state data
        key_learnings: List of learnings from the session

    Returns:
        True if updated
    """
    from datetime import date as date_type
    today = date_type.today()

    if key_learnings and handoff_context:
        handoff_context['key_learnings'] = key_learnings
    elif key_learnings:
        handoff_context = {'key_learnings': key_learnings}

    set_session_state(
        session_type=session_type,
        session_date=today,
        state_data=state_data,
        handoff_context=handoff_context
    )
    return True
