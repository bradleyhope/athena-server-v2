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


@router.post("/trigger/athena-thinking-sync")
async def trigger_athena_thinking_sync():
    """Synchronously trigger ATHENA THINKING for debugging."""
    from jobs.athena_thinking import run_athena_thinking
    
    try:
        result = await run_athena_thinking()
        return {"message": "ATHENA THINKING completed", "result": result}
    except Exception as e:
        return {"message": "ATHENA THINKING failed", "error": str(e)}


@router.post("/trigger/manus-test")
async def trigger_manus_test():
    """Direct Manus API test for debugging."""
    from integrations.manus_api import create_manus_task
    
    try:
        result = await create_manus_task(
            task_prompt="This is a test session. Please acknowledge and confirm you can see this message.",
            model="manus-1.6",
            connectors=["9c27c684-2f4f-4d33-8fcf-51664ea15c00"],
            session_type="general"
        )
        return {"message": "Manus test completed", "result": result}
    except Exception as e:
        import traceback
        return {"message": "Manus test failed", "error": str(e), "traceback": traceback.format_exc()}


@router.get("/thinking/live")
async def get_live_thinking():
    """
    Get live thinking status - shows what Athena is currently thinking.
    This is a convenience endpoint that combines session info with recent thoughts.
    """
    from db.neon import db_cursor
    from datetime import datetime, timedelta
    
    with db_cursor() as cursor:
        # Get today's active thinking session
        cursor.execute("""
            SELECT manus_task_id, manus_task_url, updated_at
            FROM active_sessions
            WHERE session_type = 'athena_thinking'
            AND session_date = CURRENT_DATE
            ORDER BY updated_at DESC
            LIMIT 1
        """)
        session_row = cursor.fetchone()
        
        session_info = None
        if session_row:
            session_info = {
                "task_id": session_row['manus_task_id'],
                "task_url": session_row['manus_task_url'],
                "updated_at": session_row['updated_at'].isoformat() if session_row['updated_at'] else None
            }
        
        # Get recent thoughts (last 2 hours)
        since = datetime.utcnow() - timedelta(hours=2)
        cursor.execute("""
            SELECT id, session_id, thought_type, content, confidence, phase, created_at
            FROM thinking_log
            WHERE created_at > %s
            ORDER BY created_at DESC
            LIMIT 20
        """, (since,))
        
        thoughts = [
            {
                "id": str(row['id']),
                "session_id": row['session_id'],
                "type": row['thought_type'],
                "content": row['content'][:200] + "..." if len(row['content']) > 200 else row['content'],
                "confidence": row['confidence'],
                "phase": row['phase'],
                "timestamp": row['created_at'].isoformat() if row['created_at'] else None
            }
            for row in cursor.fetchall()
        ]
        
        # Get thought type counts for today
        cursor.execute("""
            SELECT thought_type, COUNT(*) as count
            FROM thinking_log
            WHERE created_at > CURRENT_DATE
            GROUP BY thought_type
        """)
        type_counts = {row['thought_type']: row['count'] for row in cursor.fetchall()}
    
    return {
        "status": "active" if thoughts else "idle",
        "session": session_info,
        "thought_counts_today": type_counts,
        "recent_thoughts": thoughts
    }


@router.post("/trigger/morning-sessions")
async def trigger_morning_sessions(background_tasks: BackgroundTasks):
    """Manually trigger the Workspace & Agenda session."""
    from jobs.morning_sessions import run_morning_sessions
    
    background_tasks.add_task(run_morning_sessions)
    return {"message": "Morning session (Workspace & Agenda) triggered", "status": "running"}


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


@router.post("/trigger/hourly-broadcast")
async def trigger_hourly_broadcast(background_tasks: BackgroundTasks):
    """Manually trigger an hourly thought broadcast."""
    from jobs.hourly_broadcast import run_hourly_broadcast
    
    background_tasks.add_task(run_hourly_broadcast)
    return {"message": "Hourly broadcast triggered", "status": "running"}


@router.post("/trigger/hourly-broadcast-sync")
async def trigger_hourly_broadcast_sync():
    """Synchronously trigger an hourly thought broadcast (for testing)."""
    from jobs.hourly_broadcast import run_hourly_broadcast
    
    try:
        result = await run_hourly_broadcast()
        return {"message": "Hourly broadcast completed", "result": result}
    except Exception as e:
        import traceback
        return {"message": "Hourly broadcast failed", "error": str(e), "traceback": traceback.format_exc()}


@router.post("/sessions/send-message")
async def send_message_to_session(
    session_type: str,
    message: str
):
    """
    Send a message to an active Manus session.
    This is used for hourly broadcasts and other notifications.
    
    Args:
        session_type: Type of session (workspace_agenda, athena_thinking)
        message: The message content to send
    """
    from db.neon import get_active_session
    import httpx
    
    # Get the active session
    session = get_active_session(session_type)
    if not session:
        raise HTTPException(
            status_code=404, 
            detail=f"No active {session_type} session found"
        )
    
    task_id = session.get('manus_task_id')
    if not task_id:
        raise HTTPException(
            status_code=400,
            detail="Session has no task_id"
        )
    
    # Send message to the Manus session
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{settings.MANUS_API_BASE}/tasks/{task_id}/messages",
                headers={
                    "API_KEY": settings.MANUS_API_KEY,
                    "Content-Type": "application/json"
                },
                json={"content": message}
            )
            
            if response.status_code in [200, 201]:
                return {
                    "status": "sent",
                    "task_id": task_id,
                    "message_length": len(message)
                }
            else:
                logger.warning(f"Failed to send message to Manus: {response.status_code}")
                return {
                    "status": "failed",
                    "error": f"Manus API returned {response.status_code}",
                    "task_id": task_id
                }
    except Exception as e:
        logger.error(f"Error sending message to session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/broadcasts/recent")
async def get_recent_broadcasts():
    """
    Get recent broadcasts from the Athena Broadcasts Notion database.
    This is a convenience endpoint for checking what's been broadcast.
    """
    import httpx
    
    notion_api_key = settings.NOTION_API_KEY
    if not notion_api_key:
        raise HTTPException(status_code=500, detail="NOTION_API_KEY not configured")
    
    broadcasts_db_id = "70b8cb6eff9845d98492ce16c4e2e9aa"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"https://api.notion.com/v1/databases/{broadcasts_db_id}/query",
                headers={
                    "Authorization": f"Bearer {notion_api_key}",
                    "Content-Type": "application/json",
                    "Notion-Version": "2022-06-28"
                },
                json={
                    "sorts": [{"property": "Timestamp", "direction": "descending"}],
                    "page_size": 10
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                broadcasts = []
                for page in data.get("results", []):
                    props = page.get("properties", {})
                    broadcasts.append({
                        "id": page.get("id"),
                        "title": props.get("Name", {}).get("title", [{}])[0].get("text", {}).get("content", ""),
                        "type": props.get("Type", {}).get("select", {}).get("name", ""),
                        "priority": props.get("Priority", {}).get("select", {}).get("name", ""),
                        "status": props.get("Status", {}).get("select", {}).get("name", ""),
                        "timestamp": props.get("Timestamp", {}).get("date", {}).get("start", "")
                    })
                return {"count": len(broadcasts), "broadcasts": broadcasts}
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Notion API error: {response.text}"
                )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching broadcasts: {e}")
        raise HTTPException(status_code=500, detail=str(e))
