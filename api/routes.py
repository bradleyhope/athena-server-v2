"""
Athena Server v2 - API Routes
REST endpoints for Athena data and manual triggers.
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks

from db.neon import (
    check_db_health,
    get_recent_observations,
    get_recent_patterns,
    get_latest_synthesis,
    get_pending_drafts,
    get_canonical_memory,
)

logger = logging.getLogger("athena.api")

router = APIRouter()


# Health check
@router.get("/health")
async def health_check():
    """Detailed health status."""
    db_healthy = await check_db_health()
    
    return {
        "status": "healthy" if db_healthy else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "database": "ok" if db_healthy else "error",
            "scheduler": "ok"
        }
    }


# Data endpoints
@router.get("/observations")
async def list_observations(limit: int = 50, source_type: Optional[str] = None):
    """Get recent observations."""
    try:
        observations = get_recent_observations(limit=limit, source_type=source_type)
        return {
            "count": len(observations),
            "observations": observations
        }
    except Exception as e:
        logger.error(f"Failed to get observations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/patterns")
async def list_patterns(limit: int = 20):
    """Get recent patterns."""
    try:
        patterns = get_recent_patterns(limit=limit)
        return {
            "count": len(patterns),
            "patterns": patterns
        }
    except Exception as e:
        logger.error(f"Failed to get patterns: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/synthesis")
async def get_synthesis():
    """Get the latest synthesis."""
    try:
        synthesis = get_latest_synthesis()
        if not synthesis:
            return {"message": "No synthesis available yet"}
        return synthesis
    except Exception as e:
        logger.error(f"Failed to get synthesis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/drafts")
async def list_drafts():
    """Get pending email drafts."""
    try:
        drafts = get_pending_drafts()
        return {
            "count": len(drafts),
            "drafts": drafts
        }
    except Exception as e:
        logger.error(f"Failed to get drafts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/brief")
async def get_morning_brief():
    """
    Get the morning brief data.
    Combines synthesis, patterns, drafts, and calendar for the daily brief.
    """
    try:
        synthesis = get_latest_synthesis()
        patterns = get_recent_patterns(limit=10)
        drafts = get_pending_drafts()
        canonical = get_canonical_memory()
        
        # Get today's observations
        observations = get_recent_observations(limit=100)
        
        # Filter for action items
        action_items = [
            obs for obs in observations 
            if obs.get('priority') in ['high', 'urgent']
        ]
        
        return {
            "generated_at": datetime.utcnow().isoformat(),
            "synthesis": synthesis,
            "patterns": patterns,
            "pending_drafts": drafts,
            "action_items": action_items,
            "canonical_memory_count": len(canonical)
        }
    except Exception as e:
        logger.error(f"Failed to generate brief: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Manual trigger endpoints
@router.post("/trigger/observation")
async def trigger_observation_burst(background_tasks: BackgroundTasks):
    """Manually trigger an observation burst."""
    from jobs.observation_burst import run_observation_burst
    
    background_tasks.add_task(run_observation_burst)
    return {"message": "Observation burst triggered", "status": "running"}


@router.post("/trigger/pattern")
async def trigger_pattern_detection(background_tasks: BackgroundTasks):
    """Manually trigger pattern detection."""
    from jobs.pattern_detection import run_pattern_detection
    
    background_tasks.add_task(run_pattern_detection)
    return {"message": "Pattern detection triggered", "status": "running"}


@router.post("/trigger/synthesis")
async def trigger_synthesis(background_tasks: BackgroundTasks):
    """Manually trigger synthesis."""
    from jobs.synthesis import run_synthesis
    
    background_tasks.add_task(run_synthesis)
    return {"message": "Synthesis triggered", "status": "running"}


@router.post("/trigger/morning-sessions")
async def trigger_morning_sessions(background_tasks: BackgroundTasks):
    """Manually trigger morning Manus sessions."""
    from jobs.morning_sessions import create_athena_thinking, create_agenda_workspace
    
    background_tasks.add_task(create_athena_thinking)
    background_tasks.add_task(create_agenda_workspace)
    return {"message": "Morning sessions triggered", "status": "running"}
