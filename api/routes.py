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


@router.post("/drafts/{draft_id}/reject")
async def reject_draft(draft_id: str, reason: Optional[str] = None):
    """Reject a pending email draft."""
    from db.neon import db_cursor
    
    try:
        with db_cursor() as cursor:
            # Check if draft exists
            cursor.execute("SELECT id, status FROM email_drafts WHERE id = %s", (draft_id,))
            draft = cursor.fetchone()
            
            if not draft:
                raise HTTPException(status_code=404, detail="Draft not found")
            
            # Update status to rejected
            cursor.execute("""
                UPDATE email_drafts 
                SET status = 'rejected', 
                    reviewed_at = NOW(),
                    review_notes = %s
                WHERE id = %s
            """, (reason or "Rejected by user", draft_id))
            
        return {
            "success": True,
            "draft_id": draft_id,
            "status": "rejected",
            "reason": reason
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reject draft {draft_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/drafts/{draft_id}/approve")
async def approve_draft(draft_id: str):
    """Approve a pending email draft for sending."""
    from db.neon import db_cursor
    
    try:
        with db_cursor() as cursor:
            # Check if draft exists
            cursor.execute("SELECT id, status FROM email_drafts WHERE id = %s", (draft_id,))
            draft = cursor.fetchone()
            
            if not draft:
                raise HTTPException(status_code=404, detail="Draft not found")
            
            # Update status to approved
            cursor.execute("""
                UPDATE email_drafts 
                SET status = 'approved', 
                    reviewed_at = NOW()
                WHERE id = %s
            """, (draft_id,))
            
        return {
            "success": True,
            "draft_id": draft_id,
            "status": "approved"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to approve draft {draft_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/drafts/reject-bulk")
async def reject_drafts_bulk(draft_ids: list[str], reason: Optional[str] = None):
    """Reject multiple drafts at once."""
    from db.neon import db_cursor
    
    try:
        rejected = []
        with db_cursor() as cursor:
            for draft_id in draft_ids:
                cursor.execute("""
                    UPDATE email_drafts 
                    SET status = 'rejected', 
                        reviewed_at = NOW(),
                        review_notes = %s
                    WHERE id = %s AND status = 'pending_review'
                    RETURNING id
                """, (reason or "Bulk rejected", draft_id))
                result = cursor.fetchone()
                if result:
                    rejected.append(draft_id)
            
        return {
            "success": True,
            "rejected_count": len(rejected),
            "rejected_ids": rejected,
            "reason": reason
        }
    except Exception as e:
        logger.error(f"Failed to bulk reject drafts: {e}")
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
async def trigger_athena_thinking(background_tasks: BackgroundTasks, force: bool = False):
    """
    Manually trigger ATHENA THINKING session (hybrid: server-side + Manus broadcast).

    Args:
        force: If True, create new session even if one exists today.
    """
    from jobs.athena_thinking import run_athena_thinking

    # Can't pass force to background task easily, so check here first
    if not force:
        from db.neon import get_active_session
        from datetime import datetime
        existing = get_active_session('athena_thinking')
        if existing and existing.get('session_date') == datetime.now().date():
            return {
                "message": "ATHENA THINKING session already exists for today",
                "status": "already_exists",
                "task_id": existing.get('manus_task_id'),
                "hint": "Use force=true to create a new session"
            }

    background_tasks.add_task(run_athena_thinking, force)
    return {"message": "ATHENA THINKING triggered", "status": "running"}


@router.post("/trigger/athena-thinking-sync")
async def trigger_athena_thinking_sync(force: bool = False):
    """
    Synchronously trigger ATHENA THINKING for debugging.

    Args:
        force: If True, create new session even if one exists today.
    """
    from jobs.athena_thinking import run_athena_thinking

    try:
        result = await run_athena_thinking(force=force)
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
async def trigger_morning_sessions(force: bool = False):
    """
    Manually trigger the Workspace & Agenda session.

    Args:
        force: If True, create new session even if one exists today.
    """
    from jobs.morning_sessions import run_morning_sessions
    import asyncio

    # Run the async function directly and return result
    try:
        result = await run_morning_sessions(force=force)
        return {
            "message": "Morning session (Workspace & Agenda) created",
            "status": "success",
            "result": result
        }
    except Exception as e:
        import traceback
        return {
            "message": "Morning session failed",
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc()
        }


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


@router.post("/migrations/broadcasts-table")
async def run_broadcasts_migration():
    """Create the broadcasts table if it doesn't exist."""
    from db.neon import ensure_broadcasts_table
    
    try:
        ensure_broadcasts_table()
        return {"status": "ok", "message": "broadcasts table created/verified"}
    except Exception as e:
        logger.error(f"Failed to create broadcasts table: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/migrations/broadcast-idempotency")
async def run_broadcast_idempotency_migration():
    """Add unique constraint on broadcasts.session_id for idempotency."""
    from db.neon import db_cursor
    
    try:
        with db_cursor() as cursor:
            # Check if constraint already exists
            cursor.execute("""
                SELECT 1 FROM information_schema.table_constraints
                WHERE constraint_name = 'unique_broadcast_session'
                AND table_name = 'broadcasts'
            """)
            if cursor.fetchone():
                return {"status": "ok", "message": "Constraint already exists"}
        
        # Clean up duplicates first
        with db_cursor() as cursor:
            cursor.execute("""
                SELECT session_id, COUNT(*) as count
                FROM broadcasts
                GROUP BY session_id
                HAVING COUNT(*) > 1
            """)
            duplicates = cursor.fetchall()
            
            cleaned = 0
            for dup in duplicates:
                session_id = dup['session_id']
                cursor.execute("""
                    DELETE FROM broadcasts
                    WHERE session_id = %s
                    AND id NOT IN (
                        SELECT id FROM broadcasts
                        WHERE session_id = %s
                        ORDER BY created_at DESC
                        LIMIT 1
                    )
                """, (session_id, session_id))
                cleaned += cursor.rowcount
        
        # Add the constraint
        with db_cursor() as cursor:
            cursor.execute("""
                ALTER TABLE broadcasts
                ADD CONSTRAINT unique_broadcast_session UNIQUE (session_id)
            """)
        
        return {
            "status": "ok",
            "message": "Unique constraint added",
            "duplicates_cleaned": cleaned
        }
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/migrations/add-indexes")
async def run_indexes_migration():
    """Add performance indexes to the database (each index in separate transaction)."""
    from db.neon import db_cursor
    
    # Each index as a separate statement - will run in separate transactions
    INDEXES = [
        "CREATE INDEX IF NOT EXISTS idx_session_state_type ON session_state(session_type)",
        "CREATE INDEX IF NOT EXISTS idx_session_state_date ON session_state(session_date)",
        "CREATE INDEX IF NOT EXISTS idx_synthesis_memory_type ON synthesis_memory(synthesis_type)",
        "CREATE INDEX IF NOT EXISTS idx_synthesis_memory_created ON synthesis_memory(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_observations_category ON observations(category)",
        "CREATE INDEX IF NOT EXISTS idx_observations_collected ON observations(collected_at)",
        "CREATE INDEX IF NOT EXISTS idx_observations_source ON observations(source_type)",
        "CREATE INDEX IF NOT EXISTS idx_patterns_type ON patterns(pattern_type)",
        "CREATE INDEX IF NOT EXISTS idx_patterns_detected ON patterns(detected_at)",
        "CREATE INDEX IF NOT EXISTS idx_patterns_confidence ON patterns(confidence)",
        "CREATE INDEX IF NOT EXISTS idx_context_windows_expires ON context_windows(expires_at)",
        "CREATE INDEX IF NOT EXISTS idx_context_windows_priority ON context_windows(priority)",
        "CREATE INDEX IF NOT EXISTS idx_entities_confidence ON entities(confidence)",
        "CREATE INDEX IF NOT EXISTS idx_entities_source ON entities(source)",
        "CREATE INDEX IF NOT EXISTS idx_entities_created ON entities(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_entity_rel_strength ON entity_relationships(strength)",
        "CREATE INDEX IF NOT EXISTS idx_entity_notes_valid_until ON entity_notes(valid_until)",
        "CREATE INDEX IF NOT EXISTS idx_entity_notes_created ON entity_notes(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_thinking_log_session_phase ON thinking_log(session_id, phase)",
        "CREATE INDEX IF NOT EXISTS idx_performance_metrics_name ON performance_metrics(metric_name)",
        "CREATE INDEX IF NOT EXISTS idx_evolution_log_confidence ON evolution_log(confidence)",
        "CREATE INDEX IF NOT EXISTS idx_evolution_log_category ON evolution_log(category)",
        "CREATE INDEX IF NOT EXISTS idx_preferences_category_key ON preferences(category, key)",
        "CREATE INDEX IF NOT EXISTS idx_core_identity_key ON core_identity(key)",
        "CREATE INDEX IF NOT EXISTS idx_broadcasts_session ON broadcasts(session_id)",
        "CREATE INDEX IF NOT EXISTS idx_broadcasts_scheduled ON broadcasts(scheduled_for)",
        "CREATE INDEX IF NOT EXISTS idx_broadcasts_status ON broadcasts(status)",
    ]
    
    created = []
    skipped = []
    
    for statement in INDEXES:
        idx_name = statement.split('idx_')[1].split(' ')[0] if 'idx_' in statement else 'unknown'
        try:
            # Each index in its own transaction
            with db_cursor() as cursor:
                cursor.execute(statement)
            created.append(f"idx_{idx_name}")
        except Exception as e:
            skipped.append({"index": f"idx_{idx_name}", "reason": str(e)})
    
    return {
        "status": "ok",
        "message": f"Created {len(created)} indexes, skipped {len(skipped)}",
        "created": created,
        "skipped": skipped
    }


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


@router.post("/trigger/editing-session")
async def trigger_editing_session(force: bool = False):
    """
    Trigger an Athena Editing Session for making safe configuration changes.

    This is a special session type where Bradley can discuss and propose changes
    to Athena's boundaries, workflows, and capabilities. All changes go through
    the evolution proposal system for safety.

    Args:
        force: If True, create new session even if one exists today.
    """
    from jobs.editing_session import run_editing_session

    try:
        result = await run_editing_session(force=force)

        if result.get("status") == "already_exists":
            return {
                "message": "Editing session already exists for today",
                "status": "already_exists",
                "task_id": result.get("task_id"),
                "task_url": result.get("task_url"),
                "hint": "Use force=true to create a new session"
            }

        return {
            "message": "Editing session created",
            "status": result.get("status"),
            "task_id": result.get("task_id"),
            "task_url": result.get("task_url"),
            "session_name": result.get("session_name"),
            "error": result.get("error"),
            "traceback": result.get("traceback"),
            "manus_result": result.get("manus_result")
        }
    except Exception as e:
        import traceback
        return {
            "message": "Editing session failed",
            "error": str(e),
            "traceback": traceback.format_exc()
        }


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



# =============================================================================
# DATABASE BROADCASTS - For ATHENA THINKING to fetch hourly broadcasts
# =============================================================================

@router.get("/broadcasts/unread")
async def get_unread_broadcasts():
    """
    Get broadcasts that haven't been read by ATHENA THINKING yet.
    This is the primary endpoint for the THINKING session to check for new broadcasts.
    """
    from db.neon import get_unread_broadcasts, mark_broadcasts_read
    
    try:
        broadcasts = get_unread_broadcasts(limit=20)
        
        # Mark them as read
        if broadcasts:
            broadcast_ids = [b['id'] for b in broadcasts]
            mark_broadcasts_read(broadcast_ids)
        
        return {
            "count": len(broadcasts),
            "broadcasts": broadcasts,
            "marked_as_read": len(broadcasts)
        }
    except Exception as e:
        logger.error(f"Failed to get unread broadcasts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/broadcasts/recent")
async def get_recent_db_broadcasts(hours: int = 24, limit: int = 20):
    """
    Get recent broadcasts from the database within a time window.
    Useful for reviewing broadcast history.
    """
    from db.neon import get_recent_broadcasts
    
    try:
        broadcasts = get_recent_broadcasts(hours=hours, limit=limit)
        return {
            "count": len(broadcasts),
            "hours": hours,
            "broadcasts": broadcasts
        }
    except Exception as e:
        logger.error(f"Failed to get recent broadcasts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/broadcasts/stats")
async def get_broadcast_stats():
    """
    Get broadcast statistics for monitoring.
    """
    from db.neon import get_broadcast_stats
    
    try:
        stats = get_broadcast_stats()
        return stats
    except Exception as e:
        logger.error(f"Failed to get broadcast stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
