"""
Athena Server v2 - Evolution API Routes

API endpoints for managing the Evolution Engine with human-in-the-loop approval.
All evolution proposals require explicit human approval before being applied.
"""

import logging
from typing import Optional, List
from datetime import datetime

import json

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

from api.errors import handle_api_errors, NotFoundError, ValidationError, OperationError
from db.neon import db_cursor
from db.brain import (
    get_evolution_proposals,
    get_core_identity,
    get_boundaries,
    get_values,
    get_workflows,
    update_identity_value,
)

logger = logging.getLogger("athena.api.evolution")

router = APIRouter(prefix="/api/v1/evolution", tags=["evolution"])


# =============================================================================
# Request/Response Models
# =============================================================================

class ApprovalRequest(BaseModel):
    """Request model for approving/rejecting a proposal."""
    approved: bool = Field(..., description="Whether to approve the proposal")
    approved_by: str = Field(..., description="Who is approving (e.g., 'bradley')")
    notes: Optional[str] = Field(None, description="Optional notes about the decision")


class ManualProposal(BaseModel):
    """Request model for creating a manual evolution proposal."""
    evolution_type: str = Field(..., description="Type of evolution")
    category: str = Field(..., description="Category: identity, boundary, value, workflow, preference")
    description: str = Field(..., description="Description of the proposed change")
    change_data: dict = Field(..., description="Specific data for the change")
    justification: Optional[str] = Field(None, description="Why this change is proposed")


# =============================================================================
# Helper Functions
# =============================================================================

def get_proposal_by_id(proposal_id: str) -> Optional[dict]:
    """Get a single evolution proposal by ID."""
    with db_cursor() as cursor:
        cursor.execute("SELECT * FROM evolution_log WHERE id = %s", (proposal_id,))
        return cursor.fetchone()


def update_proposal_status(
    proposal_id: str,
    status: str,
    approved_by: str = None,
    notes: str = None
) -> bool:
    """Update the status of an evolution proposal."""
    with db_cursor() as cursor:
        if status == "approved":
            cursor.execute("""
                UPDATE evolution_log
                SET status = %s, approved_by = %s, approved_at = NOW(),
                    impact_assessment = COALESCE(impact_assessment, '{}'::jsonb) || %s::jsonb
                WHERE id = %s
            """, (status, approved_by, f'{{"approval_notes": "{notes or ""}"}}', proposal_id))
        else:
            cursor.execute("""
                UPDATE evolution_log
                SET status = %s,
                    impact_assessment = COALESCE(impact_assessment, '{}'::jsonb) || %s::jsonb
                WHERE id = %s
            """, (status, f'{{"rejection_notes": "{notes or ""}", "rejected_by": "{approved_by or ""}"}}', proposal_id))
        return cursor.rowcount > 0


def apply_evolution_change(proposal: dict) -> dict:
    """
    Apply an approved evolution proposal.

    This function handles the actual application of changes based on the
    evolution type and category.

    Returns:
        Result dict with success status and details
    """
    evolution_type = proposal.get('evolution_type', '')
    category = proposal.get('category', '')
    change_data = proposal.get('change_data', {})

    logger.info(f"Applying evolution: {evolution_type} in {category}")

    try:
        if category == 'identity':
            key = change_data.get('key')
            new_value = change_data.get('new_value')
            if key and new_value is not None:
                success = update_identity_value(key, new_value)
                return {"success": success, "action": f"Updated identity.{key}"}
            return {"success": False, "error": "Missing key or new_value in change_data"}

        elif category == 'boundary':
            with db_cursor() as cursor:
                if change_data.get('action') == 'add':
                    cursor.execute("""
                        INSERT INTO boundaries (boundary_type, category, rule, description, requires_approval)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING id
                    """, (
                        change_data.get('boundary_type', 'soft'),
                        change_data.get('category', 'general'),
                        change_data.get('rule', ''),
                        change_data.get('description', ''),
                        change_data.get('requires_approval', True)
                    ))
                    return {"success": True, "action": "Added new boundary"}
                elif change_data.get('action') == 'update':
                    cursor.execute("""
                        UPDATE boundaries SET rule = %s, description = %s, updated_at = NOW()
                        WHERE id = %s
                    """, (
                        change_data.get('rule'),
                        change_data.get('description'),
                        change_data.get('boundary_id')
                    ))
                    return {"success": cursor.rowcount > 0, "action": "Updated boundary"}
            return {"success": False, "error": "Unknown boundary action"}

        elif category == 'value':
            with db_cursor() as cursor:
                if change_data.get('action') == 'reprioritize':
                    cursor.execute("""
                        UPDATE values SET priority = %s, updated_at = NOW()
                        WHERE id = %s
                    """, (change_data.get('new_priority'), change_data.get('value_id')))
                    return {"success": cursor.rowcount > 0, "action": "Reprioritized value"}
            return {"success": False, "error": "Unknown value action"}

        elif category == 'workflow':
            with db_cursor() as cursor:
                if change_data.get('action') == 'add':
                    cursor.execute("""
                        INSERT INTO workflows (workflow_name, description, trigger_type, trigger_config, steps, requires_approval)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        RETURNING id
                    """, (
                        change_data.get('workflow_name'),
                        change_data.get('description'),
                        change_data.get('trigger_type', 'manual'),
                        '{}',
                        change_data.get('steps', '[]'),
                        change_data.get('requires_approval', True)
                    ))
                    return {"success": True, "action": "Added new workflow"}
                elif change_data.get('action') == 'update':
                    cursor.execute("""
                        UPDATE workflows SET description = %s, steps = %s, updated_at = NOW()
                        WHERE workflow_name = %s
                    """, (
                        change_data.get('description'),
                        change_data.get('steps', '[]'),
                        change_data.get('workflow_name')
                    ))
                    return {"success": cursor.rowcount > 0, "action": "Updated workflow"}
            return {"success": False, "error": "Unknown workflow action"}

        elif category == 'preference':
            with db_cursor() as cursor:
                value = change_data.get('value')
                if not isinstance(value, str):
                    value = json.dumps(value)
                elif not (value.startswith('{') or value.startswith('[') or value.startswith('"')):
                    value = json.dumps(value)

                cursor.execute("""
                    INSERT INTO preferences (category, key, value, source, confidence)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (category, key) DO UPDATE SET
                        value = EXCLUDED.value,
                        confidence = EXCLUDED.confidence,
                        updated_at = NOW()
                """, (
                    change_data.get('category', 'general'),
                    change_data.get('key'),
                    value,
                    'evolution_engine',
                    change_data.get('confidence', 0.8)
                ))
                return {"success": True, "action": "Updated preference"}

        else:
            return {"success": False, "error": f"Unknown category: {category}"}

    except Exception as e:
        logger.error(f"Failed to apply evolution: {e}")
        return {"success": False, "error": str(e)}


def mark_proposal_applied(proposal_id: str, result: dict) -> bool:
    """Mark a proposal as applied with the result."""
    with db_cursor() as cursor:
        cursor.execute("""
            UPDATE evolution_log
            SET status = 'applied', applied_at = NOW(),
                impact_assessment = COALESCE(impact_assessment, '{}'::jsonb) || %s::jsonb
            WHERE id = %s
        """, (f'{{"application_result": {result}}}', proposal_id))
        return cursor.rowcount > 0


# =============================================================================
# API Endpoints
# =============================================================================

@router.get("/proposals")
@handle_api_errors("list proposals")
async def list_proposals(
    status: Optional[str] = Query(None, description="Filter by status: proposed, approved, rejected, applied"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(50, ge=1, le=200)
):
    """List evolution proposals."""
    with db_cursor() as cursor:
        query = "SELECT * FROM evolution_log WHERE 1=1"
        params = []

        if status:
            query += " AND status = %s"
            params.append(status)

        if category:
            query += " AND category = %s"
            params.append(category)

        query += " ORDER BY created_at DESC LIMIT %s"
        params.append(limit)

        cursor.execute(query, params)
        proposals = cursor.fetchall()

    return {"proposals": proposals, "count": len(proposals)}


@router.get("/proposals/pending")
@handle_api_errors("list pending proposals")
async def list_pending_proposals():
    """List all pending proposals awaiting approval."""
    with db_cursor() as cursor:
        cursor.execute("""
            SELECT * FROM evolution_log
            WHERE status = 'proposed'
            ORDER BY confidence DESC, created_at DESC
        """)
        proposals = cursor.fetchall()

    return {"proposals": proposals, "count": len(proposals)}


@router.get("/proposals/{proposal_id}")
@handle_api_errors("get proposal")
async def get_proposal(proposal_id: str):
    """Get a specific evolution proposal."""
    proposal = get_proposal_by_id(proposal_id)
    if not proposal:
        raise NotFoundError("Proposal not found")
    return proposal


@router.post("/proposals/{proposal_id}/review")
@handle_api_errors("review proposal")
async def review_proposal(proposal_id: str, approval: ApprovalRequest):
    """
    Review (approve or reject) an evolution proposal.

    This is the human-in-the-loop step. Approved proposals can then be applied.
    """
    proposal = get_proposal_by_id(proposal_id)
    if not proposal:
        raise NotFoundError("Proposal not found")

    if proposal['status'] != 'proposed':
        raise ValidationError(f"Proposal is already {proposal['status']}, cannot review")

    new_status = "approved" if approval.approved else "rejected"
    success = update_proposal_status(
        proposal_id,
        new_status,
        approval.approved_by,
        approval.notes
    )

    if not success:
        raise OperationError("Failed to update proposal status")

    logger.info(f"Proposal {proposal_id} {new_status} by {approval.approved_by}")

    return {
        "message": f"Proposal {new_status}",
        "proposal_id": proposal_id,
        "status": new_status,
        "approved_by": approval.approved_by
    }


@router.post("/proposals/{proposal_id}/apply")
@handle_api_errors("apply proposal")
async def apply_proposal(proposal_id: str):
    """
    Apply an approved evolution proposal.

    Only approved proposals can be applied. This makes the actual changes
    to the brain's configuration.
    """
    proposal = get_proposal_by_id(proposal_id)
    if not proposal:
        raise NotFoundError("Proposal not found")

    if proposal['status'] != 'approved':
        raise ValidationError(f"Proposal must be approved before applying. Current status: {proposal['status']}")

    result = apply_evolution_change(proposal)

    if result.get('success'):
        mark_proposal_applied(proposal_id, result)
        logger.info(f"Applied evolution proposal {proposal_id}: {result.get('action')}")
        return {
            "message": "Evolution applied successfully",
            "proposal_id": proposal_id,
            "action": result.get('action')
        }
    else:
        raise OperationError(f"Failed to apply evolution: {result.get('error')}")


@router.post("/proposals")
@handle_api_errors("create proposal")
async def create_manual_proposal(proposal: ManualProposal):
    """
    Create a manual evolution proposal.

    This allows humans to propose changes that will go through the same
    approval workflow as automated proposals.
    """
    with db_cursor() as cursor:
        cursor.execute("""
            INSERT INTO evolution_log
            (evolution_type, category, description, change_data, source, confidence, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            proposal.evolution_type,
            proposal.category,
            proposal.description,
            json.dumps(proposal.change_data),
            'manual',
            1.0,
            'proposed'
        ))
        proposal_id = str(cursor.fetchone()['id'])

    logger.info(f"Created manual evolution proposal: {proposal_id}")
    return {"id": proposal_id, "message": "Proposal created successfully"}


@router.post("/run")
@handle_api_errors("run evolution engine")
async def trigger_evolution_engine():
    """
    Manually trigger the evolution engine.

    This runs the same analysis as the weekly scheduled job but can be
    triggered on demand.
    """
    from jobs.evolution_engine import run_evolution_engine
    result = await run_evolution_engine()
    return result


@router.get("/stats")
@handle_api_errors("get evolution stats")
async def get_evolution_stats():
    """Get statistics about evolution proposals."""
    with db_cursor() as cursor:
        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM evolution_log
            GROUP BY status
        """)
        status_counts = {row['status']: row['count'] for row in cursor.fetchall()}

        cursor.execute("""
            SELECT category, COUNT(*) as count
            FROM evolution_log
            GROUP BY category
        """)
        category_counts = {row['category']: row['count'] for row in cursor.fetchall()}

        cursor.execute("""
            SELECT COUNT(*) as count
            FROM evolution_log
            WHERE created_at > NOW() - INTERVAL '7 days'
        """)
        recent_count = cursor.fetchone()['count']

        cursor.execute("""
            SELECT
                COUNT(*) FILTER (WHERE status = 'approved' OR status = 'applied') as approved,
                COUNT(*) FILTER (WHERE status = 'rejected') as rejected
            FROM evolution_log
        """)
        row = cursor.fetchone()
        total_reviewed = row['approved'] + row['rejected']
        approval_rate = row['approved'] / total_reviewed if total_reviewed > 0 else 0

    return {
        "by_status": status_counts,
        "by_category": category_counts,
        "proposals_last_7_days": recent_count,
        "approval_rate": round(approval_rate, 2),
        "total_approved": row['approved'],
        "total_rejected": row['rejected']
    }
