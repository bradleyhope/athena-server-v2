"""
Athena Server v2 - Brain API Routes
REST endpoints for the Brain 2.0 four-layer architecture.
"""

import logging
from datetime import datetime, date
from typing import Optional, List, Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

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
async def get_identity():
    """Get all core identity values."""
    try:
        identity = get_core_identity()
        return {"identity": identity}
    except Exception as e:
        logger.error(f"Failed to get identity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/identity/{key}")
async def get_identity_key(key: str):
    """Get a specific identity value."""
    try:
        value = get_identity_value(key)
        if value is None:
            raise HTTPException(status_code=404, detail=f"Identity key not found: {key}")
        return {"key": key, "value": value}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get identity key {key}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/identity/{key}")
async def update_identity_key(key: str, update: IdentityUpdate):
    """Update a mutable identity value."""
    try:
        success = update_identity_value(key, update.value, update.description)
        if not success:
            raise HTTPException(status_code=400, detail=f"Cannot update identity key: {key} (may be immutable or not found)")
        return {"status": "updated", "key": key}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update identity key {key}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/boundaries")
async def list_boundaries(
    boundary_type: Optional[str] = None,
    active_only: bool = True
):
    """Get boundaries, optionally filtered by type."""
    try:
        boundaries = get_boundaries(boundary_type, active_only)
        return {"count": len(boundaries), "boundaries": boundaries}
    except Exception as e:
        logger.error(f"Failed to get boundaries: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/boundaries/check")
async def check_action_boundary(check: BoundaryCheck):
    """Check if an action is allowed based on boundaries."""
    try:
        result = check_boundary(check.category, check.action)
        return result
    except Exception as e:
        logger.error(f"Failed to check boundary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/values")
async def list_values():
    """Get all active values ordered by priority."""
    try:
        values = get_values()
        return {"count": len(values), "values": values}
    except Exception as e:
        logger.error(f"Failed to get values: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# KNOWLEDGE ENDPOINTS
# =============================================================================

@router.get("/preferences")
async def list_preferences(category: Optional[str] = None):
    """Get all preferences, optionally filtered by category."""
    try:
        preferences = get_preferences(category)
        return {"count": len(preferences), "preferences": preferences}
    except Exception as e:
        logger.error(f"Failed to get preferences: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflows")
async def list_workflows(enabled_only: bool = True):
    """Get all workflows."""
    try:
        workflows = get_workflows(enabled_only)
        return {"count": len(workflows), "workflows": workflows}
    except Exception as e:
        logger.error(f"Failed to get workflows: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflows/{workflow_name}")
async def get_workflow_by_name(workflow_name: str):
    """Get a specific workflow by name."""
    try:
        workflow = get_workflow(workflow_name)
        if not workflow:
            raise HTTPException(status_code=404, detail=f"Workflow not found: {workflow_name}")
        return workflow
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow {workflow_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workflows")
async def create_new_workflow(workflow: WorkflowCreate):
    """Create a new workflow."""
    try:
        workflow_id = create_workflow(
            workflow.workflow_name,
            workflow.description,
            workflow.trigger_type,
            workflow.trigger_config,
            workflow.steps,
            workflow.requires_approval
        )
        return {"status": "created", "id": workflow_id, "workflow_name": workflow.workflow_name}
    except Exception as e:
        logger.error(f"Failed to create workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workflows/{workflow_name}/executed")
async def record_workflow_execution(workflow_name: str, success: bool = True):
    """Record that a workflow was executed."""
    try:
        update_workflow_execution(workflow_name, success)
        return {"status": "recorded", "workflow_name": workflow_name, "success": success}
    except Exception as e:
        logger.error(f"Failed to record workflow execution: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# STATE ENDPOINTS
# =============================================================================

@router.get("/context/{session_id}")
async def get_session_context(session_id: str, context_type: Optional[str] = None):
    """Get context windows for a session."""
    try:
        contexts = get_context_window(session_id, context_type)
        return {"count": len(contexts), "contexts": contexts}
    except Exception as e:
        logger.error(f"Failed to get context: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/context")
async def create_context_window(context: ContextWindowCreate):
    """Create a new context window."""
    try:
        context_id = set_context_window(
            context.session_id,
            context.context_type,
            context.context_data,
            context.priority,
            context.expires_at
        )
        return {"status": "created", "id": context_id}
    except Exception as e:
        logger.error(f"Failed to create context: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/context/{session_id}")
async def clear_session_context(session_id: str):
    """Clear all context windows for a session."""
    try:
        count = clear_context_windows(session_id)
        return {"status": "cleared", "count": count}
    except Exception as e:
        logger.error(f"Failed to clear context: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/actions/pending")
async def list_pending_actions(
    status: str = "pending",
    priority: Optional[str] = None
):
    """Get pending actions."""
    try:
        actions = get_pending_actions(status, priority)
        return {"count": len(actions), "actions": actions}
    except Exception as e:
        logger.error(f"Failed to get pending actions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/actions")
async def create_action(action: PendingActionCreate):
    """Create a new pending action."""
    try:
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
    except Exception as e:
        logger.error(f"Failed to create action: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/actions/{action_id}/approve")
async def approve_action(action_id: str, approval: ActionApproval):
    """Approve a pending action."""
    try:
        success = approve_pending_action(action_id, approval.approved_by, approval.reason)
        if not success:
            raise HTTPException(status_code=400, detail="Action not found or not pending")
        return {"status": "approved", "id": action_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to approve action: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/actions/{action_id}/reject")
async def reject_action(action_id: str, approval: ActionApproval):
    """Reject a pending action."""
    try:
        success = reject_pending_action(action_id, approval.approved_by, approval.reason)
        if not success:
            raise HTTPException(status_code=400, detail="Action not found or not pending")
        return {"status": "rejected", "id": action_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reject action: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/actions/{action_id}/execute")
async def execute_action(action_id: str, result: Optional[dict] = None):
    """Mark an action as executed."""
    try:
        success = execute_pending_action(action_id, result)
        if not success:
            raise HTTPException(status_code=400, detail="Action not found or not approved")
        return {"status": "executed", "id": action_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to execute action: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_type}")
async def get_session(session_type: str, session_date: Optional[date] = None):
    """Get session state."""
    try:
        state = get_session_state(session_type, session_date)
        if not state:
            return {"status": "no_session", "session_type": session_type}
        return state
    except Exception as e:
        logger.error(f"Failed to get session state: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/session")
async def update_session(state: SessionStateUpdate):
    """Create or update session state."""
    try:
        session_id = set_session_state(
            state.session_type,
            state.session_date,
            state.manus_task_id,
            state.manus_task_url,
            state.state_data,
            state.handoff_context
        )
        return {"status": "updated", "id": session_id}
    except Exception as e:
        logger.error(f"Failed to update session state: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# EVOLUTION ENDPOINTS
# =============================================================================

@router.get("/evolution/proposals")
async def list_evolution_proposals(status: str = "proposed"):
    """Get evolution proposals."""
    try:
        proposals = get_evolution_proposals(status)
        return {"count": len(proposals), "proposals": proposals}
    except Exception as e:
        logger.error(f"Failed to get evolution proposals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/evolution")
async def create_evolution_proposal(evolution: EvolutionLog):
    """Log a new evolution proposal."""
    try:
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
    except Exception as e:
        logger.error(f"Failed to create evolution proposal: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/evolution/{evolution_id}/approve")
async def approve_evolution_proposal(evolution_id: str, approved_by: str):
    """Approve an evolution proposal."""
    try:
        success = approve_evolution(evolution_id, approved_by)
        if not success:
            raise HTTPException(status_code=400, detail="Evolution not found or not proposed")
        return {"status": "approved", "id": evolution_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to approve evolution: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/evolution/{evolution_id}/apply")
async def apply_evolution_proposal(evolution_id: str):
    """Apply an approved evolution."""
    try:
        success = apply_evolution(evolution_id)
        if not success:
            raise HTTPException(status_code=400, detail="Evolution not found or not approved")
        record_evolution_time()
        return {"status": "applied", "id": evolution_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to apply evolution: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics")
async def list_metrics(
    metric_type: Optional[str] = None,
    since: Optional[datetime] = None
):
    """Get performance metrics."""
    try:
        metrics = get_metrics(metric_type, since)
        return {"count": len(metrics), "metrics": metrics}
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/metrics")
async def create_metric(metric: MetricRecord):
    """Record a performance metric."""
    try:
        metric_id = record_metric(
            metric.metric_type,
            metric.metric_name,
            metric.metric_value,
            metric.period_start,
            metric.period_end,
            metric.dimensions
        )
        return {"status": "created", "id": metric_id}
    except Exception as e:
        logger.error(f"Failed to record metric: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/feedback")
async def list_unprocessed_feedback():
    """Get unprocessed feedback."""
    try:
        feedback = get_unprocessed_feedback()
        return {"count": len(feedback), "feedback": feedback}
    except Exception as e:
        logger.error(f"Failed to get feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/feedback")
async def create_feedback(feedback: FeedbackRecord):
    """Record user feedback."""
    try:
        feedback_id = record_feedback(
            feedback.feedback_type,
            feedback.target_type,
            feedback.feedback_data,
            feedback.target_id,
            feedback.sentiment
        )
        return {"status": "created", "id": feedback_id}
    except Exception as e:
        logger.error(f"Failed to record feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/feedback/{feedback_id}/processed")
async def mark_feedback_as_processed(feedback_id: str, evolution_id: Optional[str] = None):
    """Mark feedback as processed."""
    try:
        success = mark_feedback_processed(feedback_id, evolution_id)
        if not success:
            raise HTTPException(status_code=400, detail="Feedback not found")
        return {"status": "processed", "id": feedback_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to mark feedback processed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# STATUS ENDPOINTS
# =============================================================================

@router.get("/status")
async def get_status():
    """Get brain status."""
    try:
        status = get_brain_status()
        if not status:
            return {"status": "unknown", "message": "Brain status not initialized"}
        return status
    except Exception as e:
        logger.error(f"Failed to get brain status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/status")
async def update_status(update: BrainStatusUpdate):
    """Update brain status."""
    try:
        success = update_brain_status(update.status, update.config)
        if not success:
            raise HTTPException(status_code=400, detail="No updates provided")
        return {"status": "updated"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update brain status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# COMPOSITE ENDPOINTS
# =============================================================================

@router.get("/full-context")
async def get_full_context():
    """
    Get the complete brain context.
    This is the primary endpoint for loading Athena's brain into a Manus session.
    """
    try:
        context = get_full_brain_context()
        return context
    except Exception as e:
        logger.error(f"Failed to get full brain context: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session-brief/{session_type}")
async def get_brief_for_session(session_type: str):
    """
    Get a brief for starting a specific session type.
    This provides the essential context needed to start a session.
    """
    try:
        brief = get_session_brief(session_type)
        return brief
    except Exception as e:
        logger.error(f"Failed to get session brief: {e}")
        raise HTTPException(status_code=500, detail=str(e))
