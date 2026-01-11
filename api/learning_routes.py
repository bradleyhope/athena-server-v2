"""
Learning Routes - API for extracting and storing session learnings

This module provides endpoints for:
1. Submitting session reports with learnings
2. Extracting rules from learnings and creating evolution proposals
3. Approving learnings to become active rules
"""

import logging
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from db.neon import db_cursor
# Auth dependency defined locally to avoid circular imports
from fastapi import Header

async def verify_api_key(authorization: str = Header(None)):
    """Verify API key for protected endpoints."""
    from config import settings
    if not settings.ATHENA_API_KEY:
        return True
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization format")
    token = authorization.replace("Bearer ", "")
    if token != settings.ATHENA_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True

logger = logging.getLogger("athena.api.learning")
router = APIRouter(prefix="/api/v1/learning", tags=["learning"])


class LearningItem(BaseModel):
    """A single learning from a session"""
    category: str  # task_creation, email, scheduling, communication, architecture
    rule: str  # The rule or learning
    description: str  # Detailed explanation
    target: str  # boundary, preference, or canonical
    severity: str = "medium"  # low, medium, high


class SessionReport(BaseModel):
    """A session report with learnings"""
    session_date: str
    session_type: str  # workspace_agenda, thinking, etc.
    accomplishments: List[str]
    learnings: List[LearningItem]
    tips_for_tomorrow: List[str]
    manus_task_id: Optional[str] = None


class LearningApproval(BaseModel):
    """Approval for a learning to become active"""
    learning_id: str
    approved: bool
    notes: Optional[str] = None


@router.post("/submit-report")
async def submit_session_report(report: SessionReport, api_key: str = Depends(verify_api_key)):
    """
    Submit a session report with learnings.
    Creates evolution proposals for each learning that requires approval.
    """
    try:
        with db_cursor() as cur:
            # Store the session report
            cur.execute("""
                INSERT INTO session_reports (session_date, session_type, accomplishments, 
                    learnings, tips_for_tomorrow, manus_task_id, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
                RETURNING id
            """, (
                report.session_date,
                report.session_type,
                json.dumps(report.accomplishments),
                json.dumps([l.dict() for l in report.learnings]),
                json.dumps(report.tips_for_tomorrow),
                report.manus_task_id
            ))
            report_id = cur.fetchone()[0]
            
            # Create evolution proposals for each learning
            proposals_created = []
            for learning in report.learnings:
                # Determine the target table and create proposal
                proposal_data = {
                    "category": learning.category,
                    "rule": learning.rule,
                    "description": learning.description,
                    "target": learning.target,
                    "source": f"Session {report.session_date}"
                }
                
                cur.execute("""
                    INSERT INTO evolution_log (evolution_type, category, proposed_change, 
                        status, created_at)
                    VALUES (%s, %s, %s, 'pending', NOW())
                    RETURNING id
                """, (
                    f"learning_{learning.target}",
                    learning.category,
                    json.dumps(proposal_data)
                ))
                proposal_id = cur.fetchone()[0]
                proposals_created.append({
                    "id": str(proposal_id),
                    "category": learning.category,
                    "rule": learning.rule,
                    "target": learning.target
                })
            
            return {
                "status": "success",
                "report_id": str(report_id),
                "proposals_created": len(proposals_created),
                "proposals": proposals_created
            }
            
    except Exception as e:
        logger.error(f"Error submitting session report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/approve/{proposal_id}")
async def approve_learning(proposal_id: str, approval: LearningApproval, 
                          api_key: str = Depends(verify_api_key)):
    """
    Approve or reject a learning proposal.
    If approved, the learning becomes an active rule in the appropriate table.
    """
    try:
        with db_cursor() as cur:
            # Get the proposal
            cur.execute("""
                SELECT evolution_type, category, proposed_change, status
                FROM evolution_log WHERE id = %s
            """, (proposal_id,))
            row = cur.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="Proposal not found")
            
            evolution_type, category, proposed_change, status = row
            
            if status != 'pending':
                raise HTTPException(status_code=400, detail=f"Proposal already {status}")
            
            change_data = json.loads(proposed_change) if isinstance(proposed_change, str) else proposed_change
            
            if approval.approved:
                # Apply the learning to the appropriate table
                target = change_data.get("target", "boundary")
                
                if target == "boundary":
                    cur.execute("""
                        INSERT INTO boundaries (boundary_type, category, rule, description, active, created_at)
                        VALUES ('hard', %s, %s, %s, true, NOW())
                    """, (change_data["category"], change_data["rule"], change_data["description"]))
                    
                elif target == "preference":
                    cur.execute("""
                        INSERT INTO preferences (key, value, category, updated_at)
                        VALUES (%s, %s, %s, NOW())
                    """, (
                        change_data["rule"].lower().replace(" ", "_")[:50],
                        json.dumps({"rule": change_data["rule"], "description": change_data["description"]}),
                        change_data["category"]
                    ))
                    
                elif target == "canonical":
                    cur.execute("""
                        INSERT INTO canonical_memory (category, key, value, description, active, 
                            approved_at, approved_in_session, created_at)
                        VALUES (%s, %s, %s, %s, true, NOW(), %s, NOW())
                    """, (
                        change_data["category"],
                        change_data["rule"].lower().replace(" ", "_")[:50],
                        json.dumps({"rule": change_data["rule"]}),
                        change_data["description"],
                        change_data.get("source", "Manual approval")
                    ))
                
                # Update proposal status
                cur.execute("""
                    UPDATE evolution_log SET status = 'approved', 
                        reviewed_at = NOW(), review_notes = %s
                    WHERE id = %s
                """, (approval.notes, proposal_id))
                
                return {
                    "status": "approved",
                    "target": target,
                    "rule": change_data["rule"],
                    "message": f"Learning applied to {target}s"
                }
            else:
                # Reject the proposal
                cur.execute("""
                    UPDATE evolution_log SET status = 'rejected',
                        reviewed_at = NOW(), review_notes = %s
                    WHERE id = %s
                """, (approval.notes, proposal_id))
                
                return {
                    "status": "rejected",
                    "rule": change_data["rule"],
                    "message": "Learning rejected"
                }
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving learning: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pending")
async def get_pending_learnings(api_key: str = Depends(verify_api_key)):
    """Get all pending learning proposals awaiting approval."""
    try:
        with db_cursor() as cur:
            cur.execute("""
                SELECT id, evolution_type, category, proposed_change, created_at
                FROM evolution_log 
                WHERE status = 'pending' AND evolution_type LIKE 'learning_%'
                ORDER BY created_at DESC
            """)
            rows = cur.fetchall()
            
            proposals = []
            for row in rows:
                change_data = json.loads(row[3]) if isinstance(row[3], str) else row[3]
                proposals.append({
                    "id": str(row[0]),
                    "type": row[1],
                    "category": row[2],
                    "rule": change_data.get("rule"),
                    "description": change_data.get("description"),
                    "target": change_data.get("target"),
                    "source": change_data.get("source"),
                    "created_at": row[4].isoformat() if row[4] else None
                })
            
            return {
                "count": len(proposals),
                "proposals": proposals
            }
            
    except Exception as e:
        logger.error(f"Error getting pending learnings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/active-rules")
async def get_active_rules(api_key: str = Depends(verify_api_key)):
    """
    Get all active rules from boundaries, preferences, and canonical memory.
    This is what sessions should fetch to apply learned rules.
    """
    try:
        with db_cursor() as cur:
            # Get active boundaries
            cur.execute("""
                SELECT category, rule, description, boundary_type
                FROM boundaries WHERE active = true
                ORDER BY category, created_at DESC
            """)
            boundaries = [{"category": r[0], "rule": r[1], "description": r[2], "type": r[3]} 
                         for r in cur.fetchall()]
            
            # Get preferences
            cur.execute("""
                SELECT category, key, value
                FROM preferences
                ORDER BY category, updated_at DESC
            """)
            preferences = [{"category": r[0], "key": r[1], "value": r[2]} 
                          for r in cur.fetchall()]
            
            # Get active canonical memory
            cur.execute("""
                SELECT category, key, value, description
                FROM canonical_memory WHERE active = true
                ORDER BY category, created_at DESC
            """)
            canonical = [{"category": r[0], "key": r[1], "value": r[2], "description": r[3]} 
                        for r in cur.fetchall()]
            
            return {
                "boundaries": {
                    "count": len(boundaries),
                    "rules": boundaries
                },
                "preferences": {
                    "count": len(preferences),
                    "rules": preferences
                },
                "canonical_memory": {
                    "count": len(canonical),
                    "facts": canonical
                }
            }
            
    except Exception as e:
        logger.error(f"Error getting active rules: {e}")
        raise HTTPException(status_code=500, detail=str(e))
