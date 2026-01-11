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
    get_all_active_sessions,
    get_todays_thinking_session,
    ensure_active_sessions_table,
)

logger = logging.getLogger("athena.api")

router = APIRouter()


# Debug endpoint - check settings
@router.get("/debug/settings")
async def debug_settings():
    """Debug settings to see what DATABASE_URL contains."""
    import os
    from config import settings
    
    return {
        "settings_database_url_length": len(settings.DATABASE_URL),
        "settings_database_url_prefix": settings.DATABASE_URL[:50] if settings.DATABASE_URL else "EMPTY",
        "env_database_url_length": len(os.getenv("DATABASE_URL", "")),
        "env_database_url_prefix": os.getenv("DATABASE_URL", "")[:50] if os.getenv("DATABASE_URL", "") else "EMPTY"
    }


# Debug endpoint - direct connection
@router.get("/debug/db")
async def debug_db():
    """Debug database connection with direct psycopg v3."""
    import psycopg
    from config import settings
    
    try:
        conn = psycopg.connect(
            settings.DATABASE_URL,
            connect_timeout=30
        )
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM observations")
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return {"status": "ok", "observations_count": count, "database_url_length": len(settings.DATABASE_URL)}
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__,
            "database_url_length": len(settings.DATABASE_URL),
            "database_url_prefix": settings.DATABASE_URL[:50] if settings.DATABASE_URL else "EMPTY"
        }


# Debug endpoint - using db_cursor
@router.get("/debug/db_cursor")
async def debug_db_cursor():
    """Debug database connection using db_cursor context manager."""
    from db.neon import db_cursor
    
    try:
        with db_cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM observations")
            result = cursor.fetchone()
            count = result['count'] if isinstance(result, dict) else result[0]
        return {"status": "ok", "observations_count": count, "method": "db_cursor"}
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__,
            "method": "db_cursor"
        }


# Debug endpoint - using get_db_connection with detailed error
@router.get("/debug/get_conn")
async def debug_get_conn():
    """Debug database connection using get_db_connection function with detailed errors."""
    import psycopg
    import time
    from config import settings
    
    errors = []
    for attempt in range(3):
        try:
            conn = psycopg.connect(
                settings.DATABASE_URL,
                connect_timeout=30
            )
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM observations")
            count = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            return {
                "status": "ok", 
                "observations_count": count, 
                "method": "get_db_connection_inline",
                "attempt": attempt + 1,
                "previous_errors": errors
            }
        except Exception as e:
            errors.append({"attempt": attempt + 1, "error": str(e), "type": type(e).__name__})
            if attempt < 2:
                time.sleep(5)
    
    return {
        "status": "error",
        "error": "All connection attempts failed",
        "errors": errors,
        "method": "get_db_connection_inline"
    }


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


@router.post("/trigger/athena-thinking")
async def trigger_athena_thinking(background_tasks: BackgroundTasks):
    """Manually trigger ATHENA THINKING session (hybrid: server-side + Manus broadcast)."""
    from jobs.athena_thinking import run_athena_thinking
    
    background_tasks.add_task(run_athena_thinking)
    return {"message": "ATHENA THINKING triggered", "status": "running"}


@router.post("/trigger/morning-sessions")
async def trigger_morning_sessions(background_tasks: BackgroundTasks):
    """Manually trigger morning Manus sessions."""
    from jobs.morning_sessions import create_athena_thinking, create_agenda_workspace
    
    background_tasks.add_task(create_athena_thinking)
    background_tasks.add_task(create_agenda_workspace)
    return {"message": "Morning sessions triggered", "status": "running"}


# Active Sessions endpoints
@router.get("/sessions/active")
async def get_active_sessions():
    """
    Get all active Manus sessions.
    Returns session IDs that Athena can use throughout the day.
    """
    try:
        sessions = get_all_active_sessions()
        return {
            "count": len(sessions),
            "sessions": sessions
        }
    except Exception as e:
        logger.error(f"Failed to get active sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/thinking")
async def get_thinking_session():
    """
    Get today's ATHENA THINKING session.
    This is the session Athena should use for deeper analysis throughout the day.
    """
    try:
        session = get_todays_thinking_session()
        if not session:
            return {
                "status": "no_session",
                "message": "No ATHENA THINKING session found for today",
                "hint": "The morning session may not have run yet, or it's a new day"
            }
        return {
            "status": "active",
            "task_id": session['manus_task_id'],
            "task_url": session['manus_task_url'],
            "session_date": str(session['session_date']),
            "updated_at": str(session['updated_at'])
        }
    except Exception as e:
        logger.error(f"Failed to get thinking session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/init-table")
async def init_sessions_table():
    """Initialize the active_sessions table if it doesn't exist."""
    try:
        ensure_active_sessions_table()
        return {"status": "ok", "message": "active_sessions table initialized"}
    except Exception as e:
        logger.error(f"Failed to initialize sessions table: {e}")
        raise HTTPException(status_code=500, detail=str(e))
