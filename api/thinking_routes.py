"""
Athena Server v2 - Think Bursts API
Allows ATHENA THINKING to broadcast thoughts in real-time.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from db.neon import db_cursor

logger = logging.getLogger("athena.api.thinking")

router = APIRouter(prefix="/thinking", tags=["thinking"])


class ThoughtCreate(BaseModel):
    """Model for creating a new thought."""
    session_id: str
    thought_type: str  # 'observation', 'analysis', 'decision', 'question', 'insight', 'action'
    content: str
    confidence: Optional[float] = None
    phase: Optional[str] = None
    metadata: Optional[dict] = None


class ThoughtResponse(BaseModel):
    """Model for thought response."""
    id: str
    session_id: str
    thought_type: str
    content: str
    confidence: Optional[float]
    phase: Optional[str]
    metadata: Optional[dict]
    created_at: str


@router.post("/log")
async def log_thought(thought: ThoughtCreate):
    """
    Log a thought from ATHENA THINKING session.
    This is the main endpoint for think bursts.
    """
    logger.info(f"Logging thought: type={thought.thought_type}, session={thought.session_id}")
    
    with db_cursor() as cursor:
        # Serialize metadata to JSON string for JSONB column
        metadata_json = json.dumps(thought.metadata) if thought.metadata else None
        
        cursor.execute("""
            INSERT INTO thinking_log (session_id, thought_type, content, confidence, phase, metadata)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, created_at
        """, (
            thought.session_id,
            thought.thought_type,
            thought.content,
            thought.confidence,
            thought.phase,
            metadata_json
        ))
        
        result = cursor.fetchone()
        thought_id = str(result['id'])
        created_at = result['created_at'].isoformat() if result['created_at'] else None
    
    logger.info(f"Thought logged: id={thought_id}")
    
    return {
        "id": thought_id,
        "message": "Thought logged successfully",
        "created_at": created_at
    }


@router.get("/status/{session_id}")
async def get_thinking_status(session_id: str, limit: int = 10):
    """
    Get the current thinking status for a session.
    Returns recent thoughts and current phase.
    """
    with db_cursor() as cursor:
        # Get recent thoughts
        cursor.execute("""
            SELECT id, thought_type, content, confidence, phase, metadata, created_at
            FROM thinking_log
            WHERE session_id = %s
            ORDER BY created_at DESC
            LIMIT %s
        """, (session_id, limit))
        
        rows = cursor.fetchall()
        
        thoughts = []
        current_phase = None
        
        for row in rows:
            thought = {
                "id": str(row['id']),
                "type": row['thought_type'],
                "content": row['content'],
                "confidence": row['confidence'],
                "phase": row['phase'],
                "metadata": row['metadata'],
                "timestamp": row['created_at'].isoformat() if row['created_at'] else None
            }
            thoughts.append(thought)
            
            # Track the most recent phase
            if row['phase'] and not current_phase:
                current_phase = row['phase']
        
        # Get thought counts by type
        cursor.execute("""
            SELECT thought_type, COUNT(*) as count
            FROM thinking_log 
            WHERE session_id = %s 
            GROUP BY thought_type
        """, (session_id,))
        
        type_counts = {row['thought_type']: row['count'] for row in cursor.fetchall()}
        
        # Get pending questions
        cursor.execute("""
            SELECT id, content, created_at
            FROM thinking_log
            WHERE session_id = %s AND thought_type = 'question'
            ORDER BY created_at DESC
            LIMIT 5
        """, (session_id,))
        
        pending_questions = [
            {"id": str(row['id']), "content": row['content'], "timestamp": row['created_at'].isoformat() if row['created_at'] else None}
            for row in cursor.fetchall()
        ]
    
    return {
        "session_id": session_id,
        "status": "active" if thoughts else "no_activity",
        "current_phase": current_phase,
        "thought_counts": type_counts,
        "recent_thoughts": thoughts,
        "pending_questions": pending_questions
    }


@router.get("/recent")
async def get_recent_thoughts(hours: int = 24, thought_type: Optional[str] = None, limit: int = 50):
    """
    Get recent thoughts across all sessions.
    Useful for monitoring Athena's overall thinking activity.
    """
    with db_cursor() as cursor:
        since = datetime.utcnow() - timedelta(hours=hours)
        
        if thought_type:
            cursor.execute("""
                SELECT id, session_id, thought_type, content, confidence, phase, metadata, created_at
                FROM thinking_log
                WHERE created_at > %s AND thought_type = %s
                ORDER BY created_at DESC
                LIMIT %s
            """, (since, thought_type, limit))
        else:
            cursor.execute("""
                SELECT id, session_id, thought_type, content, confidence, phase, metadata, created_at
                FROM thinking_log
                WHERE created_at > %s
                ORDER BY created_at DESC
                LIMIT %s
            """, (since, limit))
        
        rows = cursor.fetchall()
        
        thoughts = [
            {
                "id": str(row['id']),
                "session_id": row['session_id'],
                "type": row['thought_type'],
                "content": row['content'],
                "confidence": row['confidence'],
                "phase": row['phase'],
                "metadata": row['metadata'],
                "timestamp": row['created_at'].isoformat() if row['created_at'] else None
            }
            for row in rows
        ]
    
    return {
        "count": len(thoughts),
        "hours": hours,
        "thoughts": thoughts
    }


@router.get("/sessions/active")
async def get_active_thinking_sessions(hours: int = 24):
    """
    Get all sessions with thinking activity in the last N hours.
    """
    with db_cursor() as cursor:
        since = datetime.utcnow() - timedelta(hours=hours)
        
        cursor.execute("""
            SELECT 
                session_id,
                COUNT(*) as thought_count,
                MIN(created_at) as first_thought,
                MAX(created_at) as last_thought,
                array_agg(DISTINCT thought_type) as thought_types
            FROM thinking_log
            WHERE created_at > %s
            GROUP BY session_id
            ORDER BY MAX(created_at) DESC
        """, (since,))
        
        rows = cursor.fetchall()
        
        sessions = [
            {
                "session_id": row['session_id'],
                "thought_count": row['thought_count'],
                "first_thought": row['first_thought'].isoformat() if row['first_thought'] else None,
                "last_thought": row['last_thought'].isoformat() if row['last_thought'] else None,
                "thought_types": row['thought_types'] if row['thought_types'] else []
            }
            for row in rows
        ]
    
    return {
        "count": len(sessions),
        "hours": hours,
        "sessions": sessions
    }


@router.delete("/session/{session_id}")
async def clear_session_thoughts(session_id: str):
    """
    Clear all thoughts for a session.
    Useful for resetting or cleanup.
    """
    with db_cursor() as cursor:
        cursor.execute("""
            DELETE FROM thinking_log WHERE session_id = %s
            RETURNING id
        """, (session_id,))
        
        deleted = cursor.fetchall()
    
    return {
        "message": f"Cleared {len(deleted)} thoughts for session {session_id}",
        "deleted_count": len(deleted)
    }
