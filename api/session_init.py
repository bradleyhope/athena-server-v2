"""
Athena Server v2 - Session Initialization API
Provides brain-driven context for Manus sessions at startup.
This replaces the Notion-dependent initialization flow.
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from db.brain import (
    get_full_brain_context,
    get_session_brief,
    get_brain_status,
    get_core_identity,
    get_boundaries,
    get_values,
    get_workflows,
    get_pending_actions,
    get_evolution_proposals,
    get_session_state,
    update_session_state,
)

logger = logging.getLogger("athena.api.session_init")

router = APIRouter(prefix="/session", tags=["Session Initialization"])


# =============================================================================
# RESPONSE MODELS
# =============================================================================

class SessionInitResponse(BaseModel):
    """Response for session initialization."""
    session_type: str
    brain_version: str
    brain_status: str
    identity: dict
    boundaries_summary: dict
    values_count: int
    workflows_enabled: int
    pending_actions_count: int
    evolution_proposals_count: int
    handoff_context: Optional[dict] = None
    system_prompt: str
    initialized_at: str


class SessionHandoffRequest(BaseModel):
    """Request to store session handoff context."""
    session_type: str
    handoff_context: dict
    key_learnings: Optional[list] = None


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/init/{session_type}", response_model=SessionInitResponse)
async def initialize_session(session_type: str):
    """
    Initialize a Manus session with brain context.
    
    This is the primary entry point for new sessions. It provides:
    - Identity, boundaries, values, and workflows
    - Any pending actions or evolution proposals
    - Handoff context from previous sessions
    - A generated system prompt
    
    Args:
        session_type: Type of session (athena_thinking, agenda_workspace, general)
    """
    logger.info(f"Initializing session: {session_type}")
    
    try:
        # Get brain status
        status = get_brain_status()
        if not status:
            raise HTTPException(status_code=503, detail="Brain not available")
        
        # Get session brief
        brief = get_session_brief(session_type)
        
        # Generate system prompt
        from integrations.brain_context import generate_brain_system_prompt
        system_prompt = generate_brain_system_prompt(session_type)
        
        # Get counts
        boundaries = get_boundaries()
        hard_count = len([b for b in boundaries if b['boundary_type'] == 'hard'])
        soft_count = len([b for b in boundaries if b['boundary_type'] == 'soft'])
        
        workflows = get_workflows()
        enabled_count = len([w for w in workflows if w['enabled']])
        
        return SessionInitResponse(
            session_type=session_type,
            brain_version=status.get('version', '2.0'),
            brain_status=status.get('status', 'unknown'),
            identity=brief['identity'],
            boundaries_summary={'hard': hard_count, 'soft': soft_count},
            values_count=len(brief['values']),
            workflows_enabled=enabled_count,
            pending_actions_count=brief['pending_actions_count'],
            evolution_proposals_count=brief['evolution_proposals_count'],
            handoff_context=brief.get('handoff_context'),
            system_prompt=system_prompt,
            initialized_at=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Session initialization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/handoff")
async def store_session_handoff(request: SessionHandoffRequest):
    """
    Store handoff context for the next session.
    
    Called at the end of a session to pass context to future sessions.
    """
    logger.info(f"Storing handoff for session type: {request.session_type}")
    
    try:
        update_session_state(
            session_type=request.session_type,
            handoff_context=request.handoff_context,
            key_learnings=request.key_learnings
        )
        
        return {
            "status": "success",
            "session_type": request.session_type,
            "stored_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to store handoff: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/context/full")
async def get_full_context():
    """
    Get the complete brain context.
    
    This returns all brain data for sessions that need full access.
    """
    try:
        context = get_full_brain_context()
        return {
            "status": "success",
            "context": context,
            "retrieved_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get full context: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/context/identity")
async def get_identity_context():
    """Get just the identity layer context."""
    try:
        identity = get_core_identity()
        boundaries = get_boundaries()
        values = get_values()
        
        return {
            "identity": identity,
            "boundaries": boundaries,
            "values": values
        }
    except Exception as e:
        logger.error(f"Failed to get identity context: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/context/operational")
async def get_operational_context():
    """Get operational context (workflows, pending items)."""
    try:
        workflows = get_workflows()
        pending_actions = get_pending_actions()
        evolution_proposals = get_evolution_proposals()
        
        return {
            "workflows": workflows,
            "pending_actions": pending_actions,
            "evolution_proposals": evolution_proposals
        }
    except Exception as e:
        logger.error(f"Failed to get operational context: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def session_health():
    """Check if session initialization is available."""
    try:
        status = get_brain_status()
        return {
            "status": "healthy" if status else "degraded",
            "brain_status": status.get('status') if status else 'unavailable',
            "brain_version": status.get('version') if status else 'unknown',
            "checked_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "checked_at": datetime.utcnow().isoformat()
        }
