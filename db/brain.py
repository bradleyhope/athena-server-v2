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
    
    # Merge key_learnings into handoff_context if provided
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


# =============================================================================
# PERFORMANCE METRICS (Simple)
# =============================================================================

def record_performance_metric(
    metric_name: str,
    metric_value: float,
    metric_unit: str = 'count',
    context: Dict = None
) -> str:
    """
    Record a simple performance metric.
    
    Args:
        metric_name: Name of the metric
        metric_value: Numeric value
        metric_unit: Unit of measurement
        context: Additional context data
        
    Returns:
        Metric ID
    """
    now = datetime.utcnow()
    return record_metric(
        metric_type='system',
        metric_name=metric_name,
        metric_value=metric_value,
        period_start=now,
        period_end=now,
        dimensions={'unit': metric_unit, 'context': context or {}}
    )


# =============================================================================
# DAILY IMPRESSIONS
# =============================================================================

def store_daily_impression(
    impression_date: date,
    category: str,
    content: str,
    confidence: float = 0.8,
    source_data: Dict = None
) -> str:
    """
    Store a daily impression in synthesis_memory.
    
    Args:
        impression_date: Date of the impression
        category: relationship|opportunity|risk|theme
        content: The impression text
        confidence: Confidence score 0.0-1.0
        source_data: Source emails/events that led to this impression
        
    Returns:
        Memory ID
    """
    with db_cursor() as cursor:
        cursor.execute("""
            INSERT INTO synthesis_memory (
                synthesis_type, content, confidence_score, 
                source_observations, created_at
            ) VALUES (%s, %s, %s, %s, NOW())
            RETURNING id
        """, (
            f"impression_{category}",
            json.dumps({
                "date": impression_date.isoformat(),
                "category": category,
                "content": content,
                "confidence": confidence
            }),
            confidence,
            json.dumps(source_data) if source_data else None
        ))
        result = cursor.fetchone()
        logger.info(f"Stored daily impression: {category}")
        return str(result['id'])


def store_daily_impressions_batch(impression_date: date, impressions: List[Dict]) -> List[str]:
    """
    Store multiple impressions at once.
    
    Args:
        impression_date: Date of the impressions
        impressions: List of impression dicts with category, content, confidence
        
    Returns:
        List of memory IDs
    """
    ids = []
    for imp in impressions:
        imp_id = store_daily_impression(
            impression_date=impression_date,
            category=imp.get("category", "theme"),
            content=imp.get("content", ""),
            confidence=imp.get("confidence", 0.8),
            source_data=imp.get("sources")
        )
        ids.append(imp_id)
    return ids


def get_recent_impressions(days: int = 7, category: str = None) -> List[Dict]:
    """
    Get recent impressions from synthesis_memory.
    
    Args:
        days: Number of days to look back
        category: Optional filter by category
        
    Returns:
        List of impression records
    """
    with db_cursor() as cursor:
        query = """
            SELECT id, content, confidence_score, created_at
            FROM synthesis_memory
            WHERE synthesis_type LIKE 'impression_%'
            AND created_at > NOW() - INTERVAL '%s days'
        """
        params = [days]
        
        if category:
            query += " AND synthesis_type = %s"
            params.append(f"impression_{category}")
        
        query += " ORDER BY created_at DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        impressions = []
        for row in rows:
            content = json.loads(row['content']) if isinstance(row['content'], str) else row['content']
            impressions.append({
                "id": str(row['id']),
                "date": content.get("date"),
                "category": content.get("category"),
                "content": content.get("content"),
                "confidence": row['confidence_score'],
                "created_at": row['created_at'].isoformat() if row['created_at'] else None
            })
        
        return impressions


def get_todays_impressions() -> List[Dict]:
    """Get impressions from today."""
    today = date.today()
    with db_cursor() as cursor:
        cursor.execute("""
            SELECT id, content, confidence_score, created_at
            FROM synthesis_memory
            WHERE synthesis_type LIKE 'impression_%'
            AND DATE(created_at) = %s
            ORDER BY created_at DESC
        """, (today,))
        rows = cursor.fetchall()
        
        impressions = []
        for row in rows:
            content = json.loads(row['content']) if isinstance(row['content'], str) else row['content']
            impressions.append({
                "id": str(row['id']),
                "category": content.get("category"),
                "content": content.get("content"),
                "confidence": row['confidence_score']
            })
        
        return impressions



# =============================================================================
# PREFERENCES FUNCTIONS (KNOWLEDGE LAYER)
# =============================================================================

def get_preferences(category: str = None) -> List[Dict]:
    """Get all preferences, optionally filtered by category."""
    with db_cursor() as cursor:
        if category:
            cursor.execute("""
                SELECT id, category, key, value, confidence, source, learned_from, created_at, updated_at
                FROM preferences
                WHERE category = %s
                ORDER BY category, confidence DESC
            """, (category,))
        else:
            cursor.execute("""
                SELECT id, category, key, value, confidence, source, learned_from, created_at, updated_at
                FROM preferences
                ORDER BY category, confidence DESC
            """)
        rows = cursor.fetchall()
        return [
            {
                "id": str(row['id']),
                "category": row['category'],
                "key": row['key'],
                "value": row['value'],
                "confidence": float(row['confidence']) if row['confidence'] else 0.5,
                "source": row['source'],
                "learned_from": row['learned_from'],
                "created_at": row['created_at'].isoformat() if row['created_at'] else None,
                "updated_at": row['updated_at'].isoformat() if row['updated_at'] else None,
            }
            for row in rows
        ]


def get_preference(category: str, key: str) -> Optional[Dict]:
    """Get a specific preference by category and key."""
    with db_cursor() as cursor:
        cursor.execute("""
            SELECT id, category, key, value, confidence, source, learned_from, created_at, updated_at
            FROM preferences
            WHERE category = %s AND key = %s
        """, (category, key))
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "id": str(row['id']),
            "category": row['category'],
            "key": row['key'],
            "value": row['value'],
            "confidence": float(row['confidence']) if row['confidence'] else 0.5,
            "source": row['source'],
            "learned_from": row['learned_from'],
            "created_at": row['created_at'].isoformat() if row['created_at'] else None,
            "updated_at": row['updated_at'].isoformat() if row['updated_at'] else None,
        }


def set_preference(category: str, key: str, value: str, confidence: float = 0.5, source: str = "manual", learned_from: str = None) -> str:
    """Create or update a preference."""
    with db_cursor() as cursor:
        cursor.execute("""
            INSERT INTO preferences (category, key, value, confidence, source, learned_from)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (category, key) DO UPDATE SET
                value = EXCLUDED.value,
                confidence = EXCLUDED.confidence,
                source = EXCLUDED.source,
                learned_from = EXCLUDED.learned_from,
                updated_at = NOW()
            RETURNING id
        """, (category, key, value, confidence, source, learned_from))
        return str(cursor.fetchone()['id'])


# =============================================================================
# CONTINUOUS STATE CONTEXT (for self-awareness)
# =============================================================================

def get_recent_sessions(days: int = 7) -> List[Dict]:
    """Get recent Athena sessions for continuity."""
    with db_cursor() as cursor:
        cursor.execute("""
            SELECT session_type, session_date, manus_task_id, manus_task_url, updated_at
            FROM active_sessions
            WHERE session_date >= CURRENT_DATE - INTERVAL '%s days'
            ORDER BY session_date DESC, updated_at DESC
        """, (days,))
        return [
            {
                "type": row['session_type'],
                "date": row['session_date'].strftime("%Y-%m-%d") if row['session_date'] else None,
                "task_id": row['manus_task_id'],
                "url": row['manus_task_url']
            }
            for row in cursor.fetchall()
        ]


def get_recent_observations(limit: int = 10) -> List[Dict]:
    """Get recent observations for context."""
    with db_cursor() as cursor:
        cursor.execute("""
            SELECT category, content, source, confidence, created_at
            FROM observations
            ORDER BY created_at DESC
            LIMIT %s
        """, (limit,))
        return [
            {
                "category": row['category'],
                "content": row['content'][:150] if row['content'] else None,
                "source": row['source'],
                "confidence": row['confidence'],
                "when": row['created_at'].strftime("%Y-%m-%d %H:%M") if row['created_at'] else None
            }
            for row in cursor.fetchall()
        ]


def get_recent_patterns(limit: int = 5) -> List[Dict]:
    """Get recent detected patterns."""
    with db_cursor() as cursor:
        cursor.execute("""
            SELECT pattern_type, description, confidence, evidence_count, detected_at
            FROM patterns
            ORDER BY detected_at DESC
            LIMIT %s
        """, (limit,))
        return [
            {
                "type": row['pattern_type'],
                "description": row['description'][:150] if row['description'] else None,
                "confidence": row['confidence'],
                "evidence_count": row['evidence_count'],
                "when": row['detected_at'].strftime("%Y-%m-%d") if row['detected_at'] else None
            }
            for row in cursor.fetchall()
        ]


def get_recent_synthesis(limit: int = 3) -> List[Dict]:
    """Get recent synthesis/conclusions."""
    with db_cursor() as cursor:
        cursor.execute("""
            SELECT synthesis_date, executive_summary, key_insights, synthesis_number
            FROM synthesis_memory
            WHERE executive_summary IS NOT NULL
            ORDER BY synthesis_date DESC
            LIMIT %s
        """, (limit,))
        return [
            {
                "date": row['synthesis_date'].strftime("%Y-%m-%d") if row['synthesis_date'] else None,
                "summary": row['executive_summary'][:200] if row['executive_summary'] else None,
                "insights": row['key_insights'][:200] if row['key_insights'] else None,
                "number": row['synthesis_number']
            }
            for row in cursor.fetchall()
        ]


def get_recent_impressions(limit: int = 5) -> List[Dict]:
    """Get recent daily impressions."""
    with db_cursor() as cursor:
        cursor.execute("""
            SELECT category, content, confidence_score, created_at
            FROM synthesis_memory
            WHERE content IS NOT NULL AND category IS NOT NULL
            ORDER BY created_at DESC
            LIMIT %s
        """, (limit,))
        return [
            {
                "category": row['category'],
                "content": row['content'][:150] if row['content'] else None,
                "confidence": row['confidence_score'],
                "when": row['created_at'].strftime("%Y-%m-%d") if row['created_at'] else None
            }
            for row in cursor.fetchall()
        ]


def get_pending_actions_list() -> List[Dict]:
    """Get all pending actions waiting for approval."""
    with db_cursor() as cursor:
        cursor.execute("""
            SELECT action_type, description, priority, context, created_at
            FROM pending_actions
            WHERE status = 'pending'
            ORDER BY priority DESC, created_at ASC
        """)
        return [
            {
                "type": row['action_type'],
                "description": row['description'][:100] if row['description'] else None,
                "priority": row['priority'],
                "context": row['context'],
                "waiting_since": row['created_at'].strftime("%Y-%m-%d %H:%M") if row['created_at'] else None
            }
            for row in cursor.fetchall()
        ]


def get_recent_feedback(limit: int = 5) -> List[Dict]:
    """Get recent feedback from Bradley."""
    with db_cursor() as cursor:
        cursor.execute("""
            SELECT feedback_type, content, sentiment, context, received_at
            FROM feedback_history
            ORDER BY received_at DESC
            LIMIT %s
        """, (limit,))
        return [
            {
                "type": row['feedback_type'],
                "content": row['content'][:150] if row['content'] else None,
                "sentiment": row['sentiment'],
                "context": row['context'],
                "when": row['received_at'].strftime("%Y-%m-%d") if row['received_at'] else None
            }
            for row in cursor.fetchall()
        ]


def get_recent_evolution_proposals(limit: int = 5) -> List[Dict]:
    """Get recent evolution/learning proposals."""
    with db_cursor() as cursor:
        cursor.execute("""
            SELECT proposal_type, description, rationale, status, created_at, reviewed_at
            FROM evolution_log
            ORDER BY created_at DESC
            LIMIT %s
        """, (limit,))
        return [
            {
                "type": row['proposal_type'],
                "description": row['description'][:150] if row['description'] else None,
                "rationale": row['rationale'][:100] if row['rationale'] else None,
                "status": row['status'],
                "proposed": row['created_at'].strftime("%Y-%m-%d") if row['created_at'] else None,
                "reviewed": row['reviewed_at'].strftime("%Y-%m-%d") if row['reviewed_at'] else None
            }
            for row in cursor.fetchall()
        ]


def get_open_questions() -> List[Dict]:
    """Get questions Athena has asked but not yet answered."""
    with db_cursor() as cursor:
        cursor.execute("""
            SELECT content, phase, created_at
            FROM thinking_log
            WHERE thought_type = 'question'
            AND created_at > CURRENT_DATE - INTERVAL '7 days'
            ORDER BY created_at DESC
            LIMIT 10
        """)
        return [
            {
                "question": row['content'],
                "phase": row['phase'],
                "asked": row['created_at'].strftime("%Y-%m-%d %H:%M") if row['created_at'] else None
            }
            for row in cursor.fetchall()
        ]


def get_learning_stats() -> Dict[str, Any]:
    """Get statistics about Athena's learning activity."""
    with db_cursor() as cursor:
        # Count proposals by status
        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM evolution_log
            GROUP BY status
        """)
        status_counts = {row['status']: row['count'] for row in cursor.fetchall()}
        
        # Days since last proposal
        cursor.execute("""
            SELECT MAX(created_at) as last_proposal
            FROM evolution_log
        """)
        row = cursor.fetchone()
        last_proposal = row['last_proposal'] if row else None
        days_since_proposal = None
        if last_proposal:
            days_since_proposal = (datetime.utcnow() - last_proposal).days
        
        # Total observations this week
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM observations
            WHERE created_at > CURRENT_DATE - INTERVAL '7 days'
        """)
        observations_this_week = cursor.fetchone()['count']
        
        # Total patterns detected
        cursor.execute("SELECT COUNT(*) as count FROM patterns")
        total_patterns = cursor.fetchone()['count']
        
        return {
            "proposals_by_status": status_counts,
            "days_since_last_proposal": days_since_proposal,
            "observations_this_week": observations_this_week,
            "total_patterns_detected": total_patterns
        }


def get_continuous_state_context() -> Dict[str, Any]:
    """
    Get Athena's complete continuous state for self-awareness.
    This is the main function to call for building the system prompt.
    """
    return {
        "recent_sessions": get_recent_sessions(days=7),
        "recent_observations": get_recent_observations(limit=10),
        "recent_patterns": get_recent_patterns(limit=5),
        "recent_synthesis": get_recent_synthesis(limit=3),
        "recent_impressions": get_recent_impressions(limit=5),
        "pending_actions": get_pending_actions_list(),
        "recent_feedback": get_recent_feedback(limit=5),
        "recent_evolution": get_recent_evolution_proposals(limit=5),
        "open_questions": get_open_questions(),
        "learning_stats": get_learning_stats()
    }


# =============================================================================
# ENTITIES - Knowledge Graph for People, Organizations, Projects
# =============================================================================

def create_entity(
    entity_type: str,
    name: str,
    description: str = None,
    aliases: List[str] = None,
    metadata: Dict = None,
    access_tier: str = "default",
    source: str = None,
    confidence: float = 1.0
) -> str:
    """
    Create a new entity in the knowledge graph.
    
    Args:
        entity_type: Type of entity ('person', 'organization', 'project', 'location')
        name: Primary name of the entity
        description: Optional description
        aliases: Optional list of alternative names
        metadata: Optional type-specific metadata
        access_tier: Access tier ('default', 'vip', 'restricted')
        source: Where this entity was learned from
        confidence: Confidence in accuracy (0.0-1.0)
        
    Returns:
        UUID of the created entity
    """
    with db_cursor() as cursor:
        cursor.execute("""
            INSERT INTO entities (entity_type, name, description, aliases, metadata, access_tier, source, confidence)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            entity_type,
            name,
            description,
            json.dumps(aliases or []),
            json.dumps(metadata or {}),
            access_tier,
            source,
            confidence
        ))
        entity_id = str(cursor.fetchone()['id'])
        logger.info(f"Created entity: {entity_type}/{name} ({entity_id})")
        return entity_id


def get_entity(entity_id: str) -> Optional[Dict]:
    """Get an entity by ID."""
    with db_cursor() as cursor:
        cursor.execute("SELECT * FROM entities WHERE id = %s", (entity_id,))
        return cursor.fetchone()


def get_entity_by_name(name: str, entity_type: str = None) -> Optional[Dict]:
    """
    Get an entity by name (case-insensitive) or alias.
    
    Args:
        name: Name to search for
        entity_type: Optional type filter
        
    Returns:
        Entity dict or None
    """
    with db_cursor() as cursor:
        query = """
            SELECT * FROM entities 
            WHERE active = TRUE
            AND (
                LOWER(name) = LOWER(%s)
                OR aliases @> %s::jsonb
            )
        """
        params = [name, json.dumps([name.lower()])]
        
        if entity_type:
            query += " AND entity_type = %s"
            params.append(entity_type)
        
        query += " ORDER BY confidence DESC LIMIT 1"
        cursor.execute(query, params)
        return cursor.fetchone()


def search_entities(
    query: str = None,
    entity_type: str = None,
    access_tier: str = None,
    limit: int = 20
) -> List[Dict]:
    """
    Search for entities.
    
    Args:
        query: Optional text search query
        entity_type: Optional type filter
        access_tier: Optional access tier filter
        limit: Maximum results to return
        
    Returns:
        List of matching entities
    """
    with db_cursor() as cursor:
        sql = "SELECT * FROM entities WHERE active = TRUE"
        params = []
        
        if query:
            sql += " AND to_tsvector('english', name || ' ' || COALESCE(description, '')) @@ plainto_tsquery('english', %s)"
            params.append(query)
        
        if entity_type:
            sql += " AND entity_type = %s"
            params.append(entity_type)
        
        if access_tier:
            sql += " AND access_tier = %s"
            params.append(access_tier)
        
        sql += " ORDER BY confidence DESC, name LIMIT %s"
        params.append(limit)
        
        cursor.execute(sql, params)
        return cursor.fetchall()


def get_entities_by_type(entity_type: str, active_only: bool = True) -> List[Dict]:
    """Get all entities of a specific type."""
    with db_cursor() as cursor:
        query = "SELECT * FROM entities WHERE entity_type = %s"
        params = [entity_type]
        
        if active_only:
            query += " AND active = TRUE"
        
        query += " ORDER BY name"
        cursor.execute(query, params)
        return cursor.fetchall()


def get_vip_entities() -> List[Dict]:
    """Get all VIP entities (people with access_tier = 'vip')."""
    with db_cursor() as cursor:
        cursor.execute("""
            SELECT * FROM entities 
            WHERE access_tier = 'vip' AND active = TRUE
            ORDER BY name
        """)
        return cursor.fetchall()


def update_entity(
    entity_id: str,
    name: str = None,
    description: str = None,
    aliases: List[str] = None,
    metadata: Dict = None,
    access_tier: str = None,
    confidence: float = None
) -> bool:
    """
    Update an entity.
    
    Args:
        entity_id: ID of entity to update
        Other args: Fields to update (None = no change)
        
    Returns:
        True if updated
    """
    updates = []
    params = []
    
    if name is not None:
        updates.append("name = %s")
        params.append(name)
    if description is not None:
        updates.append("description = %s")
        params.append(description)
    if aliases is not None:
        updates.append("aliases = %s")
        params.append(json.dumps(aliases))
    if metadata is not None:
        updates.append("metadata = %s")
        params.append(json.dumps(metadata))
    if access_tier is not None:
        updates.append("access_tier = %s")
        params.append(access_tier)
    if confidence is not None:
        updates.append("confidence = %s")
        params.append(confidence)
    
    if not updates:
        return False
    
    updates.append("updated_at = NOW()")
    params.append(entity_id)
    
    with db_cursor() as cursor:
        cursor.execute(f"""
            UPDATE entities SET {', '.join(updates)}
            WHERE id = %s
        """, params)
        return cursor.rowcount > 0


def delete_entity(entity_id: str, soft_delete: bool = True) -> bool:
    """
    Delete an entity.
    
    Args:
        entity_id: ID of entity to delete
        soft_delete: If True, just set active=FALSE. If False, hard delete.
        
    Returns:
        True if deleted
    """
    with db_cursor() as cursor:
        if soft_delete:
            cursor.execute("UPDATE entities SET active = FALSE, updated_at = NOW() WHERE id = %s", (entity_id,))
        else:
            cursor.execute("DELETE FROM entities WHERE id = %s", (entity_id,))
        return cursor.rowcount > 0


# Entity Relationships

def create_relationship(
    source_entity_id: str,
    target_entity_id: str,
    relationship_type: str,
    description: str = None,
    strength: float = 1.0,
    start_date: date = None,
    end_date: date = None,
    metadata: Dict = None,
    source: str = None
) -> str:
    """
    Create a relationship between two entities.
    
    Args:
        source_entity_id: ID of source entity
        target_entity_id: ID of target entity
        relationship_type: Type of relationship (e.g., 'employee_of', 'works_on')
        description: Optional description
        strength: Relationship strength (0.0-1.0)
        start_date: When relationship started
        end_date: When relationship ended (None = ongoing)
        metadata: Additional metadata
        source: Where this relationship was learned from
        
    Returns:
        UUID of the created relationship
    """
    with db_cursor() as cursor:
        cursor.execute("""
            INSERT INTO entity_relationships 
            (source_entity_id, target_entity_id, relationship_type, description, strength, start_date, end_date, metadata, source)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (source_entity_id, target_entity_id, relationship_type) 
            DO UPDATE SET 
                description = EXCLUDED.description,
                strength = EXCLUDED.strength,
                metadata = EXCLUDED.metadata,
                updated_at = NOW()
            RETURNING id
        """, (
            source_entity_id,
            target_entity_id,
            relationship_type,
            description,
            strength,
            start_date,
            end_date,
            json.dumps(metadata or {}),
            source
        ))
        return str(cursor.fetchone()['id'])


def get_entity_relationships(entity_id: str, direction: str = "both") -> List[Dict]:
    """
    Get all relationships for an entity.
    
    Args:
        entity_id: ID of the entity
        direction: 'outgoing', 'incoming', or 'both'
        
    Returns:
        List of relationships with entity details
    """
    with db_cursor() as cursor:
        if direction == "outgoing":
            cursor.execute("""
                SELECT r.*, e.name as target_name, e.entity_type as target_type
                FROM entity_relationships r
                JOIN entities e ON r.target_entity_id = e.id
                WHERE r.source_entity_id = %s AND r.active = TRUE
                ORDER BY r.strength DESC
            """, (entity_id,))
        elif direction == "incoming":
            cursor.execute("""
                SELECT r.*, e.name as source_name, e.entity_type as source_type
                FROM entity_relationships r
                JOIN entities e ON r.source_entity_id = e.id
                WHERE r.target_entity_id = %s AND r.active = TRUE
                ORDER BY r.strength DESC
            """, (entity_id,))
        else:
            cursor.execute("""
                SELECT r.*, 
                    se.name as source_name, se.entity_type as source_type,
                    te.name as target_name, te.entity_type as target_type
                FROM entity_relationships r
                JOIN entities se ON r.source_entity_id = se.id
                JOIN entities te ON r.target_entity_id = te.id
                WHERE (r.source_entity_id = %s OR r.target_entity_id = %s) AND r.active = TRUE
                ORDER BY r.strength DESC
            """, (entity_id, entity_id))
        
        return cursor.fetchall()


# Entity Notes

def add_entity_note(
    entity_id: str,
    note_type: str,
    content: str,
    importance: str = "normal",
    valid_until: datetime = None,
    source: str = None
) -> str:
    """
    Add a note to an entity.
    
    Args:
        entity_id: ID of the entity
        note_type: Type of note ('interaction', 'preference', 'context', 'reminder')
        content: Note content
        importance: 'low', 'normal', 'high', 'critical'
        valid_until: When this note expires
        source: Where this note came from
        
    Returns:
        UUID of the created note
    """
    with db_cursor() as cursor:
        cursor.execute("""
            INSERT INTO entity_notes (entity_id, note_type, content, importance, valid_until, source)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (entity_id, note_type, content, importance, valid_until, source))
        return str(cursor.fetchone()['id'])


def get_entity_notes(entity_id: str, note_type: str = None, include_expired: bool = False) -> List[Dict]:
    """Get notes for an entity."""
    with db_cursor() as cursor:
        query = "SELECT * FROM entity_notes WHERE entity_id = %s"
        params = [entity_id]
        
        if note_type:
            query += " AND note_type = %s"
            params.append(note_type)
        
        if not include_expired:
            query += " AND (valid_until IS NULL OR valid_until > NOW())"
        
        query += " ORDER BY importance DESC, created_at DESC"
        cursor.execute(query, params)
        return cursor.fetchall()


def get_entity_context(entity_id: str) -> Dict[str, Any]:
    """
    Get complete context for an entity including relationships and notes.
    
    Args:
        entity_id: ID of the entity
        
    Returns:
        Dictionary with entity, relationships, and notes
    """
    entity = get_entity(entity_id)
    if not entity:
        return None
    
    return {
        "entity": entity,
        "relationships": get_entity_relationships(entity_id),
        "notes": get_entity_notes(entity_id),
    }
