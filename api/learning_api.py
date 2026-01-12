"""
Athena Server v2 - Learning API Endpoints

Endpoints for passive and active learning.
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from learning import (
    extract_entities_from_text,
    store_extracted_entities,
    learn_from_task_completion,
    quick_learn,
    update_working_context,
    get_current_context,
)
from api.errors import handle_api_errors

logger = logging.getLogger("athena.api.learning")

router = APIRouter(prefix="/api/learn", tags=["learning"])


# =============================================================================
# Request Models
# =============================================================================

class QuickLearnRequest(BaseModel):
    """Request to quickly learn something."""
    statement: str  # e.g., "Never create tasks from Stripe notifications"
    source: Optional[str] = "api"


class TaskCompletionRequest(BaseModel):
    """Request to learn from a completed task."""
    task_title: str
    completion_notes: Optional[str] = ""
    time_taken: Optional[str] = ""
    was_good_task: bool = True  # False if task shouldn't have been created


class ExtractEntitiesRequest(BaseModel):
    """Request to extract entities from text."""
    text: str
    context: Optional[str] = ""
    source: Optional[str] = "manual"
    store: bool = True  # Whether to store extracted entities


class ContextUpdateRequest(BaseModel):
    """Request to update working context."""
    current_focus: Optional[str] = None
    active_project: Optional[str] = None
    blocked_on: Optional[str] = None
    energy_level: Optional[str] = None  # "high", "medium", "low"


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/quick")
@handle_api_errors("quick_learn")
async def api_quick_learn(request: QuickLearnRequest):
    """
    Quick learn something. Use for statements like:
    - "Never create tasks from Stripe notifications"
    - "Always reply to John's emails within 2 hours"
    - "Bradley prefers bullet points over paragraphs"

    The system automatically classifies as boundary/preference/fact.
    """
    result = await quick_learn(
        statement=request.statement,
        source=request.source
    )

    return {
        "status": "learned" if result.get("stored") else "failed",
        "statement": request.statement,
        "classification": result.get("classification"),
        "storage_location": result.get("storage_location"),
        "message": f"Stored as {result.get('storage_location')}" if result.get("stored") else "Failed to store"
    }


@router.post("/task-completed")
@handle_api_errors("learn_from_task")
async def api_learn_from_task(request: TaskCompletionRequest):
    """
    Learn from a completed task.
    Extracts patterns, preferences, and potential workflows.

    If was_good_task is False, learns what NOT to create.
    """
    learnings = await learn_from_task_completion(
        task_title=request.task_title,
        completion_notes=request.completion_notes,
        time_taken=request.time_taken,
        was_good_task=request.was_good_task
    )

    return {
        "status": "learned",
        "task_title": request.task_title,
        "was_good_task": request.was_good_task,
        "learnings": learnings
    }


@router.post("/extract-entities")
@handle_api_errors("extract_entities")
async def api_extract_entities(request: ExtractEntitiesRequest):
    """
    Extract entities (people, companies, projects) from text.
    Optionally stores them in the brain.
    """
    extracted = await extract_entities_from_text(
        text=request.text,
        context=request.context,
        source=request.source
    )

    storage_counts = {}
    if request.store and not extracted.get("error"):
        storage_counts = await store_extracted_entities(extracted, source=request.source)

    return {
        "status": "extracted",
        "entities": extracted,
        "stored": request.store,
        "storage_counts": storage_counts
    }


@router.post("/context")
@handle_api_errors("update_context")
async def api_update_context(request: ContextUpdateRequest):
    """
    Update Bradley's current working context.
    This helps Athena understand what Bradley is focused on.
    """
    result = await update_working_context(
        current_focus=request.current_focus,
        active_project=request.active_project,
        blocked_on=request.blocked_on,
        energy_level=request.energy_level
    )

    return {
        "status": "updated",
        "context": result.get("context")
    }


@router.get("/context")
@handle_api_errors("get_context")
async def api_get_context():
    """
    Get Bradley's current working context.
    """
    context = get_current_context()
    return {
        "status": "ok",
        "context": context
    }


# =============================================================================
# Passive Learning Hooks (called internally)
# =============================================================================

async def on_email_processed(email_data: dict) -> dict:
    """
    Called when an email is processed.
    Extracts entities and learns about contacts.
    """
    text = f"{email_data.get('subject', '')} {email_data.get('body', '')}"
    sender = email_data.get('from', '')

    extracted = await extract_entities_from_text(
        text=text,
        context=f"Email from {sender}",
        source="email"
    )

    await store_extracted_entities(extracted, source="email")

    return {"processed": True, "entities_found": len(extracted.get("people", []))}


async def on_calendar_event_processed(event_data: dict) -> dict:
    """
    Called when a calendar event is processed.
    Extracts entities and learns about meetings.
    """
    text = f"{event_data.get('summary', '')} {event_data.get('description', '')}"
    attendees = event_data.get('attendees', [])

    extracted = await extract_entities_from_text(
        text=text,
        context=f"Calendar event with {len(attendees)} attendees",
        source="calendar"
    )

    await store_extracted_entities(extracted, source="calendar")

    return {"processed": True, "entities_found": len(extracted.get("people", []))}
