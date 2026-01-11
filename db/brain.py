"""
Athena Server v2 - Brain Database Module
Database operations for the Brain 2.0 four-layer architecture.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, date
import json

from db.neon import db_cursor

logger = logging.getLogger("athena.db.brain")


# =============================================================================
# LAYER 1: IDENTITY
# =============================================================================

def get_core_identity() -> Dict[str, Any]:
    """
    Get all core identity values as a dictionary.
    
    Returns:
        Dictionary of identity key-value pairs
    """
    with db_cursor() as cursor:
        cursor.execute("SELECT key, value, immutable FROM core_identity")
        rows = cursor.fetchall()
        return {row['key']: {'value': row['value'], 'immutable': row['immutable']} for row in rows}


def get_identity_value(key: str) -> Optional[Any]:
    """Get a specific identity value."""
    with db_cursor() as cursor:
        cursor.execute("SELECT value FROM core_identity WHERE key = %s", (key,))
        row = cursor.fetchone()
        return row['value'] if row else None


def update_identity_value(key: str, value: Any, description: str = None) -> bool:
    """
    Update a mutable identity value.
    
    Args:
        key: Identity key to update
        value: New value (will be JSON serialized)
        description: Optional description update
        
    Returns:
        True if updated, False if immutable or not found
    """
    with db_cursor() as cursor:
        # Check if immutable
        cursor.execute("SELECT immutable FROM core_identity WHERE key = %s", (key,))
        row = cursor.fetchone()
        if not row:
            logger.warning(f"Identity key not found: {key}")
            return False
        if row['immutable']:
            logger.warning(f"Cannot update immutable identity key: {key}")
            return False
        
        # Update
        if description:
            cursor.execute("""
                UPDATE core_identity 
                SET value = %s, description = %s, updated_at = NOW()
                WHERE key = %s
            """, (json.dumps(value), description, key))
        else:
            cursor.execute("""
                UPDATE core_identity 
                SET value = %s, updated_at = NOW()
                WHERE key = %s
            """, (json.dumps(value), key))
        
        logger.info(f"Updated identity value: {key}")
        return True


def get_boundaries(boundary_type: str = None, active_only: bool = True) -> List[Dict]:
    """
    Get boundaries, optionally filtered by type.
    
    Args:
        boundary_type: Filter by 'hard', 'soft', or 'contextual'
        active_only: Only return active boundaries
        
    Returns:
        List of boundary dictionaries
    """
    with db_cursor() as cursor:
        query = "SELECT * FROM boundaries WHERE 1=1"
        params = []
        
        if active_only:
            query += " AND active = TRUE"
        if boundary_type:
            query += " AND boundary_type = %s"
            params.append(boundary_type)
        
        query += " ORDER BY boundary_type, category"
        cursor.execute(query, params)
        return cursor.fetchall()


def check_boundary(category: str, action: str) -> Dict[str, Any]:
    """
    Check if an action is allowed based on boundaries.
    
    Args:
        category: Boundary category (e.g., 'email', 'financial')
        action: Description of the intended action
        
    Returns:
        Dictionary with 'allowed', 'requires_approval', 'boundary' keys
    """
    with db_cursor() as cursor:
        cursor.execute("""
            SELECT * FROM boundaries 
            WHERE category = %s AND active = TRUE
            ORDER BY boundary_type
        """, (category,))
        boundaries = cursor.fetchall()
        
        if not boundaries:
            return {'allowed': True, 'requires_approval': False, 'boundary': None}
        
        # Check hard boundaries first
        for b in boundaries:
            if b['boundary_type'] == 'hard':
                return {
                    'allowed': False,
                    'requires_approval': True,
                    'boundary': b
                }
        
        # Check soft boundaries
        for b in boundaries:
            if b['boundary_type'] == 'soft':
                return {
                    'allowed': True,
                    'requires_approval': b['requires_approval'],
                    'boundary': b
                }
        
        return {'allowed': True, 'requires_approval': False, 'boundary': boundaries[0]}


def get_values() -> List[Dict]:
    """Get all active values ordered by priority."""
    with db_cursor() as cursor:
        cursor.execute("""
            SELECT * FROM values 
            WHERE active = TRUE 
            ORDER BY priority
        """)
        return cursor.fetchall()


# =============================================================================
# LAYER 2: KNOWLEDGE
# =============================================================================

def get_workflows(enabled_only: bool = True) -> List[Dict]:
    """Get all workflows."""
    with db_cursor() as cursor:
        query = "SELECT * FROM workflows"
        if enabled_only:
            query += " WHERE enabled = TRUE"
        query += " ORDER BY workflow_name"
        cursor.execute(query)
        return cursor.fetchall()


def get_workflow(workflow_name: str) -> Optional[Dict]:
    """Get a specific workflow by name."""
    with db_cursor() as cursor:
        cursor.execute("SELECT * FROM workflows WHERE workflow_name = %s", (workflow_name,))
        return cursor.fetchone()


def update_workflow_execution(workflow_name: str, success: bool) -> bool:
    """
    Update workflow execution statistics.
    
    Args:
        workflow_name: Name of the workflow
        success: Whether the execution was successful
        
    Returns:
        True if updated
    """
    with db_cursor() as cursor:
        cursor.execute("""
            UPDATE workflows SET
                execution_count = execution_count + 1,
                last_executed_at = NOW(),
                success_rate = (success_rate * execution_count + %s) / (execution_count + 1)
            WHERE workflow_name = %s
        """, (1.0 if success else 0.0, workflow_name))
        return True


def create_workflow(
    workflow_name: str,
    description: str,
    trigger_type: str,
    trigger_config: Dict,
    steps: List[Dict],
    requires_approval: bool = False
) -> str:
    """Create a new workflow and return its ID."""
    with db_cursor() as cursor:
        cursor.execute("""
            INSERT INTO workflows (workflow_name, description, trigger_type, trigger_config, steps, requires_approval)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (workflow_name, description, trigger_type, json.dumps(trigger_config), json.dumps(steps), requires_approval))
        return str(cursor.fetchone()['id'])


# =============================================================================
# LAYER 3: STATE
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


# =============================================================================
# LAYER 4: EVOLUTION
# =============================================================================

def log_evolution(
    evolution_type: str,
    category: str,
    description: str,
    change_data: Dict,
    source: str,
    source_id: str = None,
    confidence: float = 0.5
) -> str:
    """Log an evolution proposal."""
    with db_cursor() as cursor:
        cursor.execute("""
            INSERT INTO evolution_log (
                evolution_type, category, description, change_data,
                source, source_id, confidence
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (evolution_type, category, description, json.dumps(change_data), source, source_id, confidence))
        return str(cursor.fetchone()['id'])


def get_evolution_proposals(status: str = 'proposed') -> List[Dict]:
    """Get evolution proposals by status."""
    with db_cursor() as cursor:
        cursor.execute("""
            SELECT * FROM evolution_log 
            WHERE status = %s 
            ORDER BY confidence DESC, created_at DESC
        """, (status,))
        return cursor.fetchall()


def approve_evolution(evolution_id: str, approved_by: str) -> bool:
    """Approve an evolution proposal."""
    with db_cursor() as cursor:
        cursor.execute("""
            UPDATE evolution_log SET
                status = 'approved',
                approved_by = %s,
                approved_at = NOW()
            WHERE id = %s AND status = 'proposed'
        """, (approved_by, evolution_id))
        return cursor.rowcount > 0


def apply_evolution(evolution_id: str) -> bool:
    """Mark an evolution as applied."""
    with db_cursor() as cursor:
        cursor.execute("""
            UPDATE evolution_log SET
                status = 'applied',
                applied_at = NOW()
            WHERE id = %s AND status = 'approved'
        """, (evolution_id,))
        return cursor.rowcount > 0


def record_metric(
    metric_type: str,
    metric_name: str,
    metric_value: float,
    period_start: datetime,
    period_end: datetime,
    dimensions: Dict = None
) -> str:
    """Record a performance metric."""
    with db_cursor() as cursor:
        cursor.execute("""
            INSERT INTO performance_metrics (
                metric_type, metric_name, metric_value,
                period_start, period_end, dimensions
            ) VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (metric_type, metric_name, metric_value, period_start, period_end, json.dumps(dimensions or {})))
        return str(cursor.fetchone()['id'])


def get_metrics(metric_type: str = None, since: datetime = None) -> List[Dict]:
    """Get performance metrics."""
    with db_cursor() as cursor:
        query = "SELECT * FROM performance_metrics WHERE 1=1"
        params = []
        
        if metric_type:
            query += " AND metric_type = %s"
            params.append(metric_type)
        if since:
            query += " AND period_start >= %s"
            params.append(since)
        
        query += " ORDER BY period_start DESC"
        cursor.execute(query, params)
        return cursor.fetchall()


def record_feedback(
    feedback_type: str,
    target_type: str,
    feedback_data: Dict,
    target_id: str = None,
    sentiment: str = None
) -> str:
    """Record user feedback."""
    with db_cursor() as cursor:
        cursor.execute("""
            INSERT INTO feedback_history (
                feedback_type, target_type, target_id, feedback_data, sentiment
            ) VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (feedback_type, target_type, target_id, json.dumps(feedback_data), sentiment))
        return str(cursor.fetchone()['id'])


def get_unprocessed_feedback() -> List[Dict]:
    """Get feedback that hasn't been processed yet."""
    with db_cursor() as cursor:
        cursor.execute("""
            SELECT * FROM feedback_history 
            WHERE processed = FALSE 
            ORDER BY created_at
        """)
        return cursor.fetchall()


def mark_feedback_processed(feedback_id: str, evolution_id: str = None) -> bool:
    """Mark feedback as processed."""
    with db_cursor() as cursor:
        cursor.execute("""
            UPDATE feedback_history SET
                processed = TRUE,
                processed_at = NOW(),
                evolution_id = %s
            WHERE id = %s
        """, (evolution_id, feedback_id))
        return cursor.rowcount > 0


# =============================================================================
# BRAIN STATUS
# =============================================================================

def get_brain_status() -> Optional[Dict]:
    """Get current brain status."""
    with db_cursor() as cursor:
        cursor.execute("SELECT * FROM brain_status LIMIT 1")
        return cursor.fetchone()


def update_brain_status(status: str = None, config: Dict = None) -> bool:
    """Update brain status."""
    with db_cursor() as cursor:
        updates = []
        params = []
        
        if status:
            updates.append("status = %s")
            params.append(status)
        if config:
            updates.append("config = %s")
            params.append(json.dumps(config))
        
        if not updates:
            return False
        
        updates.append("updated_at = NOW()")
        query = f"UPDATE brain_status SET {', '.join(updates)}"
        cursor.execute(query, params)
        return True


def record_synthesis_time() -> bool:
    """Record that a synthesis was performed."""
    with db_cursor() as cursor:
        cursor.execute("UPDATE brain_status SET last_synthesis_at = NOW()")
        return True


def record_evolution_time() -> bool:
    """Record that evolution engine ran."""
    with db_cursor() as cursor:
        cursor.execute("UPDATE brain_status SET last_evolution_at = NOW()")
        return True


def record_notion_sync_time() -> bool:
    """Record that Notion sync was performed."""
    with db_cursor() as cursor:
        cursor.execute("UPDATE brain_status SET last_notion_sync_at = NOW()")
        return True


# =============================================================================
# NOTION SYNC
# =============================================================================

def log_notion_sync(
    source_table: str,
    source_id: str,
    sync_type: str,
    notion_page_id: str = None,
    notion_database_id: str = None
) -> str:
    """Log a Notion sync operation."""
    with db_cursor() as cursor:
        cursor.execute("""
            INSERT INTO notion_sync_log (
                source_table, source_id, sync_type, notion_page_id, notion_database_id
            ) VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (source_table, source_id, sync_type, notion_page_id, notion_database_id))
        return str(cursor.fetchone()['id'])


def update_notion_sync_status(sync_id: str, status: str, error_message: str = None) -> bool:
    """Update Notion sync status."""
    with db_cursor() as cursor:
        cursor.execute("""
            UPDATE notion_sync_log SET
                sync_status = %s,
                error_message = %s,
                synced_at = CASE WHEN %s = 'success' THEN NOW() ELSE synced_at END
            WHERE id = %s
        """, (status, error_message, status, sync_id))
        return cursor.rowcount > 0


def get_pending_notion_syncs() -> List[Dict]:
    """Get pending Notion sync operations."""
    with db_cursor() as cursor:
        cursor.execute("""
            SELECT * FROM notion_sync_log 
            WHERE sync_status = 'pending' 
            ORDER BY created_at
        """)
        return cursor.fetchall()


# =============================================================================
# COMPOSITE QUERIES
# =============================================================================

def get_full_brain_context() -> Dict[str, Any]:
    """
    Get the complete brain context for a Manus session.
    This is the primary method for loading Athena's brain into a session.
    
    Returns:
        Dictionary containing all brain layers
    """
    return {
        'identity': get_core_identity(),
        'boundaries': get_boundaries(),
        'values': get_values(),
        'workflows': get_workflows(),
        'status': get_brain_status(),
        'pending_actions': get_pending_actions(),
        'evolution_proposals': get_evolution_proposals()
    }


def get_session_brief(session_type: str) -> Dict[str, Any]:
    """
    Get a brief for starting a specific session type.
    
    Args:
        session_type: Type of session (athena_thinking, agenda_workspace, etc.)
        
    Returns:
        Dictionary with relevant context for the session
    """
    identity = get_core_identity()
    boundaries = get_boundaries(active_only=True)
    values = get_values()
    status = get_brain_status()
    
    # Get recent session state for handoff
    recent_state = get_session_state(session_type)
    
    return {
        'identity': {k: v['value'] for k, v in identity.items()},
        'boundaries': [{'type': b['boundary_type'], 'category': b['category'], 'rule': b['rule']} for b in boundaries],
        'values': [{'priority': v['priority'], 'name': v['value_name'], 'description': v['description']} for v in values],
        'status': status['status'] if status else 'unknown',
        'handoff_context': recent_state['handoff_context'] if recent_state else None,
        'pending_actions_count': len(get_pending_actions()),
        'evolution_proposals_count': len(get_evolution_proposals())
    }
