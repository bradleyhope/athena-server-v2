"""
Athena Server v2 - Brain API Routes
REST endpoints for the Brain 2.0 four-layer architecture.
"""

import logging
from datetime import datetime, date
from typing import Optional, List, Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from api.errors import handle_api_errors, NotFoundError, ValidationError
from db.brain import (
    # Identity
    get_core_identity,
    get_identity_value,
    update_identity_value,
    get_boundaries,
    check_boundary,
    get_values,
    # Knowledge
    get_workflows,
    get_workflow,
    update_workflow_execution,
    create_workflow,
    get_preferences,
    # State
    get_context_window,
    set_context_window,
    clear_context_windows,
    get_pending_actions,
    create_pending_action,
    approve_pending_action,
    reject_pending_action,
    execute_pending_action,
    get_session_state,
    set_session_state,
    # Evolution
    log_evolution,
    get_evolution_proposals,
    approve_evolution,
    apply_evolution,
    record_metric,
    get_metrics,
    record_feedback,
    get_unprocessed_feedback,
    mark_feedback_processed,
    get_learning_analytics,
    get_learning_insights,
    # Status
    get_brain_status,
    update_brain_status,
    record_synthesis_time,
    record_evolution_time,
    record_notion_sync_time,
    # Composite
    get_full_brain_context,
    get_session_brief,
)

logger = logging.getLogger("athena.api.brain")

router = APIRouter(prefix="/brain", tags=["brain"])


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class IdentityUpdate(BaseModel):
    value: Any
    description: Optional[str] = None


class BoundaryCheck(BaseModel):
    category: str
    action: str


class WorkflowCreate(BaseModel):
    workflow_name: str
    description: str
    trigger_type: str
    trigger_config: dict = {}
    steps: List[dict] = []
    requires_approval: bool = False


class ContextWindowCreate(BaseModel):
    session_id: str
    context_type: str
    context_data: dict
    priority: int = 0
    expires_at: Optional[datetime] = None


class PendingActionCreate(BaseModel):
    action_type: str
    action_data: dict
    priority: str = "normal"
    requires_approval: bool = True
    source_workflow_id: Optional[str] = None
    source_synthesis_id: Optional[str] = None
    expires_at: Optional[datetime] = None


class ActionApproval(BaseModel):
    approved_by: str
    reason: Optional[str] = None


class SessionStateUpdate(BaseModel):
    session_type: str
    session_date: date
    manus_task_id: Optional[str] = None
    manus_task_url: Optional[str] = None
    state_data: Optional[dict] = None
    handoff_context: Optional[dict] = None


class EvolutionLog(BaseModel):
    evolution_type: str
    category: str
    description: str
    change_data: dict
    source: str
    source_id: Optional[str] = None
    confidence: float = 0.5


class MetricRecord(BaseModel):
    metric_type: str
    metric_name: str
    metric_value: float
    period_start: datetime
    period_end: datetime
    dimensions: Optional[dict] = None


class FeedbackRecord(BaseModel):
    feedback_type: str
    target_type: str
    feedback_data: dict
    target_id: Optional[str] = None
    sentiment: Optional[str] = None


class BrainStatusUpdate(BaseModel):
    status: Optional[str] = None
    config: Optional[dict] = None


# =============================================================================
# IDENTITY ENDPOINTS
# =============================================================================

@router.get("/identity")
@handle_api_errors("get identity")
async def get_identity():
    """Get all core identity values."""
    identity = get_core_identity()
    return {"identity": identity}


@router.get("/identity/{key}")
@handle_api_errors("get identity key")
async def get_identity_key(key: str):
    """Get a specific identity value."""
    value = get_identity_value(key)
    if value is None:
        raise NotFoundError(f"Identity key not found: {key}")
    return {"key": key, "value": value}


@router.put("/identity/{key}")
@handle_api_errors("update identity key")
async def update_identity_key(key: str, update: IdentityUpdate):
    """Update a mutable identity value."""
    success = update_identity_value(key, update.value, update.description)
    if not success:
        raise ValidationError(f"Cannot update identity key: {key} (may be immutable or not found)")
    return {"status": "updated", "key": key}


@router.get("/boundaries")
@handle_api_errors("get boundaries")
async def list_boundaries(
    boundary_type: Optional[str] = None,
    active_only: bool = True
):
    """Get boundaries, optionally filtered by type."""
    boundaries = get_boundaries(boundary_type, active_only)
    return {"count": len(boundaries), "boundaries": boundaries}


@router.post("/boundaries/check")
@handle_api_errors("check boundary")
async def check_action_boundary(check: BoundaryCheck):
    """Check if an action is allowed based on boundaries."""
    result = check_boundary(check.category, check.action)
    return result


@router.get("/values")
@handle_api_errors("get values")
async def list_values():
    """Get all active values ordered by priority."""
    values = get_values()
    return {"count": len(values), "values": values}


# =============================================================================
# KNOWLEDGE ENDPOINTS
# =============================================================================

@router.get("/preferences")
@handle_api_errors("get preferences")
async def list_preferences(category: Optional[str] = None):
    """Get all preferences, optionally filtered by category."""
    preferences = get_preferences(category)
    return {"count": len(preferences), "preferences": preferences}


@router.get("/workflows")
@handle_api_errors("get workflows")
async def list_workflows(enabled_only: bool = True):
    """Get all workflows."""
    workflows = get_workflows(enabled_only)
    return {"count": len(workflows), "workflows": workflows}


@router.get("/workflows/{workflow_name}")
@handle_api_errors("get workflow")
async def get_workflow_by_name(workflow_name: str):
    """Get a specific workflow by name."""
    workflow = get_workflow(workflow_name)
    if not workflow:
        raise NotFoundError(f"Workflow not found: {workflow_name}")
    return workflow


@router.post("/workflows")
@handle_api_errors("create workflow")
async def create_new_workflow(workflow: WorkflowCreate):
    """Create a new workflow."""
    workflow_id = create_workflow(
        workflow.workflow_name,
        workflow.description,
        workflow.trigger_type,
        workflow.trigger_config,
        workflow.steps,
        workflow.requires_approval
    )
    return {"status": "created", "id": workflow_id, "workflow_name": workflow.workflow_name}


@router.post("/workflows/{workflow_name}/executed")
@handle_api_errors("record workflow execution")
async def record_workflow_execution(workflow_name: str, success: bool = True):
    """Record that a workflow was executed."""
    update_workflow_execution(workflow_name, success)
    return {"status": "recorded", "workflow_name": workflow_name, "success": success}


# =============================================================================
# STATE ENDPOINTS
# =============================================================================

@router.get("/context/{session_id}")
@handle_api_errors("get context")
async def get_session_context(session_id: str, context_type: Optional[str] = None):
    """Get context windows for a session."""
    contexts = get_context_window(session_id, context_type)
    return {"count": len(contexts), "contexts": contexts}


@router.post("/context")
@handle_api_errors("create context")
async def create_context_window(context: ContextWindowCreate):
    """Create a new context window."""
    context_id = set_context_window(
        context.session_id,
        context.context_type,
        context.context_data,
        context.priority,
        context.expires_at
    )
    return {"status": "created", "id": context_id}


@router.delete("/context/{session_id}")
@handle_api_errors("clear context")
async def clear_session_context(session_id: str):
    """Clear all context windows for a session."""
    count = clear_context_windows(session_id)
    return {"status": "cleared", "count": count}


@router.get("/actions/pending")
@handle_api_errors("get pending actions")
async def list_pending_actions(
    status: str = "pending",
    priority: Optional[str] = None
):
    """Get pending actions."""
    actions = get_pending_actions(status, priority)
    return {"count": len(actions), "actions": actions}


@router.post("/actions")
@handle_api_errors("create action")
async def create_action(action: PendingActionCreate):
    """Create a new pending action."""
    action_id = create_pending_action(
        action.action_type,
        action.action_data,
        action.priority,
        action.requires_approval,
        action.source_workflow_id,
        action.source_synthesis_id,
        action.expires_at
    )
    return {"status": "created", "id": action_id}


@router.post("/actions/{action_id}/approve")
@handle_api_errors("approve action")
async def approve_action(action_id: str, approval: ActionApproval):
    """Approve a pending action."""
    success = approve_pending_action(action_id, approval.approved_by, approval.reason)
    if not success:
        raise ValidationError("Action not found or not pending")
    return {"status": "approved", "id": action_id}


@router.post("/actions/{action_id}/reject")
@handle_api_errors("reject action")
async def reject_action(action_id: str, approval: ActionApproval):
    """Reject a pending action."""
    success = reject_pending_action(action_id, approval.approved_by, approval.reason)
    if not success:
        raise ValidationError("Action not found or not pending")
    return {"status": "rejected", "id": action_id}


@router.post("/actions/{action_id}/execute")
@handle_api_errors("execute action")
async def execute_action(action_id: str, result: Optional[dict] = None):
    """Mark an action as executed."""
    success = execute_pending_action(action_id, result)
    if not success:
        raise ValidationError("Action not found or not approved")
    return {"status": "executed", "id": action_id}


@router.get("/session/{session_type}")
@handle_api_errors("get session state")
async def get_session(session_type: str, session_date: Optional[date] = None):
    """Get session state."""
    state = get_session_state(session_type, session_date)
    if not state:
        return {"status": "no_session", "session_type": session_type}
    return state


@router.post("/session")
@handle_api_errors("update session state")
async def update_session(state: SessionStateUpdate):
    """Create or update session state."""
    session_id = set_session_state(
        state.session_type,
        state.session_date,
        state.manus_task_id,
        state.manus_task_url,
        state.state_data,
        state.handoff_context
    )
    return {"status": "updated", "id": session_id}


# =============================================================================
# EVOLUTION ENDPOINTS
# =============================================================================

@router.get("/evolution/proposals")
@handle_api_errors("get evolution proposals")
async def list_evolution_proposals(status: str = "proposed"):
    """Get evolution proposals."""
    proposals = get_evolution_proposals(status)
    return {"count": len(proposals), "proposals": proposals}


@router.post("/evolution")
@handle_api_errors("create evolution proposal")
async def create_evolution_proposal(evolution: EvolutionLog):
    """Log a new evolution proposal."""
    evolution_id = log_evolution(
        evolution.evolution_type,
        evolution.category,
        evolution.description,
        evolution.change_data,
        evolution.source,
        evolution.source_id,
        evolution.confidence
    )
    return {"status": "created", "id": evolution_id}


@router.post("/evolution/{evolution_id}/approve")
@handle_api_errors("approve evolution")
async def approve_evolution_proposal(evolution_id: str, approved_by: str):
    """Approve an evolution proposal."""
    success = approve_evolution(evolution_id, approved_by)
    if not success:
        raise ValidationError("Evolution not found or not proposed")
    return {"status": "approved", "id": evolution_id}


@router.post("/evolution/{evolution_id}/apply")
@handle_api_errors("apply evolution")
async def apply_evolution_proposal(evolution_id: str):
    """Apply an approved evolution."""
    success = apply_evolution(evolution_id)
    if not success:
        raise ValidationError("Evolution not found or not approved")
    record_evolution_time()
    return {"status": "applied", "id": evolution_id}


@router.get("/metrics")
@handle_api_errors("get metrics")
async def list_metrics(
    metric_type: Optional[str] = None,
    since: Optional[datetime] = None
):
    """Get performance metrics."""
    metrics = get_metrics(metric_type, since)
    return {"count": len(metrics), "metrics": metrics}


@router.post("/metrics")
@handle_api_errors("record metric")
async def create_metric(metric: MetricRecord):
    """Record a performance metric."""
    metric_id = record_metric(
        metric.metric_type,
        metric.metric_name,
        metric.metric_value,
        metric.period_start,
        metric.period_end,
        metric.dimensions
    )
    return {"status": "created", "id": metric_id}


@router.get("/feedback")
@handle_api_errors("get feedback")
async def list_unprocessed_feedback():
    """Get unprocessed feedback."""
    feedback = get_unprocessed_feedback()
    return {"count": len(feedback), "feedback": feedback}


@router.post("/feedback")
@handle_api_errors("record feedback")
async def create_feedback(feedback: FeedbackRecord):
    """Record user feedback."""
    feedback_id = record_feedback(
        feedback.feedback_type,
        feedback.target_type,
        feedback.feedback_data,
        feedback.target_id,
        feedback.sentiment
    )
    return {"status": "created", "id": feedback_id}


@router.post("/feedback/{feedback_id}/processed")
@handle_api_errors("mark feedback processed")
async def mark_feedback_as_processed(feedback_id: str, evolution_id: Optional[str] = None):
    """Mark feedback as processed."""
    success = mark_feedback_processed(feedback_id, evolution_id)
    if not success:
        raise NotFoundError("Feedback not found")
    return {"status": "processed", "id": feedback_id}


# =============================================================================
# LEARNING ANALYTICS ENDPOINTS
# =============================================================================

@router.get("/analytics")
@handle_api_errors("get learning analytics")
async def get_analytics():
    """
    Get comprehensive learning analytics.
    
    Returns analytics including:
    - Proposal counts by status, category, and type
    - Approval rates
    - Trends over time
    - Most common categories
    """
    analytics = get_learning_analytics()
    return analytics


@router.get("/analytics/insights")
@handle_api_errors("get learning insights")
async def get_insights():
    """
    Get human-readable insights from learning analytics.
    
    Returns a list of insight strings based on current analytics data.
    """
    insights = get_learning_insights()
    return {"count": len(insights), "insights": insights}


# =============================================================================
# RULE EXPIRATION ENDPOINTS
# =============================================================================

@router.post("/rules/cleanup")
@handle_api_errors("cleanup expired rules")
async def cleanup_rules():
    """
    Clean up expired rules from the database.
    Marks expired boundaries and canonical memory as inactive.
    Deletes expired preferences.
    
    Returns counts of cleaned up rules by table.
    """
    from utils.context_loader import cleanup_expired_rules
    counts = cleanup_expired_rules()
    total = sum(counts.values())
    return {
        "status": "completed",
        "total_cleaned": total,
        "by_table": counts
    }


@router.post("/boundaries/{boundary_id}/expire")
@handle_api_errors("set boundary expiration")
async def set_boundary_expiration(boundary_id: str, expires_at: datetime):
    """
    Set an expiration date for a boundary.
    
    Args:
        boundary_id: UUID of the boundary
        expires_at: When the boundary should expire
    """
    from db.neon import db_cursor
    with db_cursor() as cur:
        cur.execute("""
            UPDATE boundaries SET expires_at = %s, updated_at = NOW()
            WHERE id = %s
        """, (expires_at, boundary_id))
        if cur.rowcount == 0:
            raise NotFoundError(f"Boundary not found: {boundary_id}")
    return {"status": "updated", "id": boundary_id, "expires_at": expires_at.isoformat()}


@router.post("/preferences/{preference_key}/expire")
@handle_api_errors("set preference expiration")
async def set_preference_expiration(preference_key: str, expires_at: datetime):
    """
    Set an expiration date for a preference.
    
    Args:
        preference_key: Key of the preference
        expires_at: When the preference should expire
    """
    from db.neon import db_cursor
    with db_cursor() as cur:
        cur.execute("""
            UPDATE preferences SET expires_at = %s, updated_at = NOW()
            WHERE key = %s
        """, (expires_at, preference_key))
        if cur.rowcount == 0:
            raise NotFoundError(f"Preference not found: {preference_key}")
    return {"status": "updated", "key": preference_key, "expires_at": expires_at.isoformat()}


# =============================================================================
# STATUS ENDPOINTS
# =============================================================================

@router.get("/status")
@handle_api_errors("get brain status")
async def get_status():
    """Get brain status."""
    status = get_brain_status()
    if not status:
        return {"status": "unknown", "message": "Brain status not initialized"}
    return status


@router.put("/status")
@handle_api_errors("update brain status")
async def update_status(update: BrainStatusUpdate):
    """Update brain status."""
    success = update_brain_status(update.status, update.config)
    if not success:
        raise ValidationError("No updates provided")
    return {"status": "updated"}


# =============================================================================
# COMPOSITE ENDPOINTS
# =============================================================================

@router.get("/full-context")
@handle_api_errors("get full brain context")
async def get_full_context():
    """
    Get the complete brain context.
    This is the primary endpoint for loading Athena's brain into a Manus session.
    """
    context = get_full_brain_context()
    return context


@router.get("/session-brief/{session_type}")
@handle_api_errors("get session brief")
async def get_brief_for_session(session_type: str):
    """
    Get a brief for starting a specific session type.
    This provides the essential context needed to start a session.
    """
    brief = get_session_brief(session_type)
    return brief


# =============================================================================
# MEMORY APPROVAL ENDPOINT
# =============================================================================

class MemoryApprovalRequest(BaseModel):
    """Request model for approving a memory proposal."""
    memory_id: str = Field(..., description="ID of the memory proposal to approve")
    approved_by: Optional[str] = Field(None, description="Who approved this memory (e.g., 'Bradley', 'Athena')")
    notes: Optional[str] = Field(None, description="Optional notes about the approval")


@router.post("/memory/approve")
@handle_api_errors("approve memory proposal")
async def approve_memory_proposal_endpoint(request: MemoryApprovalRequest):
    """
    Approve a memory proposal from synthesis.
    Moves it from proposals to canonical_memory.
    
    This endpoint is part of the evolution system, allowing memory proposals
    generated during synthesis to be approved and added to canonical memory.
    """
    from db.neon import db_cursor
    
    logger.info(f"Approving memory proposal: {request.memory_id}")
    
    try:
        with db_cursor() as cursor:
            # Check if the memory proposal exists
            cursor.execute("""
                SELECT * FROM memory_proposals
                WHERE id = %s AND status = 'pending'
            """, (request.memory_id,))
            
            proposal = cursor.fetchone()
            
            if not proposal:
                raise NotFoundError(f"Memory proposal {request.memory_id} not found or already processed")
            
            # Move to canonical_memory
            cursor.execute("""
                INSERT INTO canonical_memory (
                    category, subcategory, key, value, source, confidence,
                    last_verified, created_at, updated_at
                )
                VALUES (
                    %(category)s, %(subcategory)s, %(key)s, %(value)s, %(source)s, %(confidence)s,
                    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                )
                RETURNING id
            """, {
                'category': proposal['category'],
                'subcategory': proposal.get('subcategory'),
                'key': proposal['key'],
                'value': proposal['value'],
                'source': proposal.get('source', 'synthesis'),
                'confidence': proposal.get('confidence', 0.8)
            })
            
            canonical_id = cursor.fetchone()['id']
            
            # Update proposal status
            cursor.execute("""
                UPDATE memory_proposals
                SET status = 'approved',
                    approved_at = CURRENT_TIMESTAMP,
                    approved_by = %s,
                    notes = %s
                WHERE id = %s
            """, (request.approved_by or 'system', request.notes, request.memory_id))
            
            logger.info(f"✅ Memory proposal {request.memory_id} approved and moved to canonical_memory as {canonical_id}")
            
            return {
                "status": "approved",
                "memory_id": request.memory_id,
                "canonical_id": str(canonical_id),
                "message": "Memory proposal approved and added to canonical memory"
            }
            
    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Failed to approve memory proposal: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to approve memory: {str(e)}")


# =============================================================================
# DATA QUERY ENDPOINTS
# =============================================================================

@router.get("/observations")
@handle_api_errors("get observations")
async def get_observations(limit: int = 50, hours: int = None):
    """
    Get recent observations from the brain.
    
    Args:
        limit: Maximum number of observations to return (default 50)
        hours: If specified, only return observations from the last N hours
    """
    from db.brain.composite import get_recent_observations
    
    observations = get_recent_observations(limit=limit, hours=hours)
    return {
        "count": len(observations),
        "limit": limit,
        "hours": hours,
        "observations": observations
    }


@router.get("/patterns")
@handle_api_errors("get patterns")
async def get_patterns(limit: int = 20):
    """
    Get detected patterns from the brain.
    
    Args:
        limit: Maximum number of patterns to return (default 20)
    """
    from db.brain.composite import get_recent_patterns
    
    patterns = get_recent_patterns(limit=limit)
    return {
        "count": len(patterns),
        "limit": limit,
        "patterns": patterns
    }


@router.get("/synthesis")
@handle_api_errors("get synthesis")
async def get_synthesis(limit: int = 10):
    """
    Get synthesis/conclusions from the brain.
    
    Args:
        limit: Maximum number of synthesis records to return (default 10)
    """
    from db.brain.composite import get_recent_synthesis
    
    synthesis = get_recent_synthesis(limit=limit)
    return {
        "count": len(synthesis),
        "limit": limit,
        "synthesis": synthesis
    }
