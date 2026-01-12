"""
Athena Server v2 - Entity API Routes

API endpoints for managing entities (people, organizations, projects)
in the knowledge graph.
"""

import logging
from typing import Optional, List
from datetime import datetime, date

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from db.brain import (
    create_entity,
    get_entity,
    get_entity_by_name,
    search_entities,
    get_entities_by_type,
    get_vip_entities,
    update_entity,
    delete_entity,
    create_relationship,
    get_entity_relationships,
    add_entity_note,
    get_entity_notes,
    get_entity_context,
)
from api.errors import handle_api_errors, NotFoundError

logger = logging.getLogger("athena.api.entities")

router = APIRouter(prefix="/api/v1/entities", tags=["entities"])


# =============================================================================
# Request/Response Models
# =============================================================================

class EntityCreate(BaseModel):
    """Request model for creating an entity."""
    entity_type: str = Field(..., description="Type: 'person', 'organization', 'project', 'location'")
    name: str = Field(..., description="Primary name of the entity")
    description: Optional[str] = Field(None, description="Description of the entity")
    aliases: Optional[List[str]] = Field(default=[], description="Alternative names")
    metadata: Optional[dict] = Field(default={}, description="Type-specific metadata")
    access_tier: Optional[str] = Field(default="default", description="Access tier: 'default', 'vip', 'restricted'")
    source: Optional[str] = Field(None, description="Where this entity was learned from")
    confidence: Optional[float] = Field(default=1.0, ge=0.0, le=1.0, description="Confidence in accuracy")


class EntityUpdate(BaseModel):
    """Request model for updating an entity."""
    name: Optional[str] = None
    description: Optional[str] = None
    aliases: Optional[List[str]] = None
    metadata: Optional[dict] = None
    access_tier: Optional[str] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)


class RelationshipCreate(BaseModel):
    """Request model for creating a relationship."""
    source_entity_id: str = Field(..., description="ID of source entity")
    target_entity_id: str = Field(..., description="ID of target entity")
    relationship_type: str = Field(..., description="Type: 'employee_of', 'works_on', 'member_of', etc.")
    description: Optional[str] = None
    strength: Optional[float] = Field(default=1.0, ge=0.0, le=1.0)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    metadata: Optional[dict] = Field(default={})
    source: Optional[str] = None


class NoteCreate(BaseModel):
    """Request model for creating a note."""
    note_type: str = Field(..., description="Type: 'interaction', 'preference', 'context', 'reminder'")
    content: str = Field(..., description="Note content")
    importance: Optional[str] = Field(default="normal", description="'low', 'normal', 'high', 'critical'")
    valid_until: Optional[datetime] = None
    source: Optional[str] = None


# =============================================================================
# Entity Endpoints
# =============================================================================

@router.post("", status_code=201)
@handle_api_errors("create entity")
async def create_entity_endpoint(entity: EntityCreate):
    """Create a new entity."""
    entity_id = create_entity(
        entity_type=entity.entity_type,
        name=entity.name,
        description=entity.description,
        aliases=entity.aliases,
        metadata=entity.metadata,
        access_tier=entity.access_tier,
        source=entity.source,
        confidence=entity.confidence
    )
    return {"id": entity_id, "message": "Entity created successfully"}


@router.get("")
@handle_api_errors("list entities")
async def list_entities(
    query: Optional[str] = Query(None, description="Search query"),
    entity_type: Optional[str] = Query(None, description="Filter by type"),
    access_tier: Optional[str] = Query(None, description="Filter by access tier"),
    limit: int = Query(20, ge=1, le=100)
):
    """Search and list entities."""
    entities = search_entities(
        query=query,
        entity_type=entity_type,
        access_tier=access_tier,
        limit=limit
    )
    return {"entities": entities, "count": len(entities)}


@router.get("/vip")
@handle_api_errors("get VIP entities")
async def list_vip_entities():
    """Get all VIP entities."""
    entities = get_vip_entities()
    return {"entities": entities, "count": len(entities)}


@router.get("/by-name/{name}")
@handle_api_errors("get entity by name")
async def get_entity_by_name_endpoint(
    name: str,
    entity_type: Optional[str] = Query(None)
):
    """Get an entity by name (case-insensitive)."""
    entity = get_entity_by_name(name, entity_type)
    if not entity:
        raise NotFoundError("Entity not found")
    return entity


@router.get("/type/{entity_type}")
@handle_api_errors("list entities by type")
async def list_entities_by_type(entity_type: str):
    """Get all entities of a specific type."""
    entities = get_entities_by_type(entity_type)
    return {"entities": entities, "count": len(entities)}


@router.get("/{entity_id}")
@handle_api_errors("get entity")
async def get_entity_endpoint(entity_id: str):
    """Get an entity by ID."""
    entity = get_entity(entity_id)
    if not entity:
        raise NotFoundError("Entity not found")
    return entity


@router.get("/{entity_id}/context")
@handle_api_errors("get entity context")
async def get_entity_context_endpoint(entity_id: str):
    """Get complete context for an entity including relationships and notes."""
    context = get_entity_context(entity_id)
    if not context:
        raise NotFoundError("Entity not found")
    return context


@router.put("/{entity_id}")
@handle_api_errors("update entity")
async def update_entity_endpoint(entity_id: str, entity: EntityUpdate):
    """Update an entity."""
    success = update_entity(
        entity_id=entity_id,
        name=entity.name,
        description=entity.description,
        aliases=entity.aliases,
        metadata=entity.metadata,
        access_tier=entity.access_tier,
        confidence=entity.confidence
    )
    if not success:
        raise NotFoundError("Entity not found or no changes")
    return {"message": "Entity updated successfully"}


@router.delete("/{entity_id}")
@handle_api_errors("delete entity")
async def delete_entity_endpoint(entity_id: str, hard_delete: bool = Query(False)):
    """Delete an entity (soft delete by default)."""
    success = delete_entity(entity_id, soft_delete=not hard_delete)
    if not success:
        raise NotFoundError("Entity not found")
    return {"message": "Entity deleted successfully"}


# =============================================================================
# Relationship Endpoints
# =============================================================================

@router.post("/relationships", status_code=201)
@handle_api_errors("create relationship")
async def create_relationship_endpoint(relationship: RelationshipCreate):
    """Create a relationship between two entities."""
    rel_id = create_relationship(
        source_entity_id=relationship.source_entity_id,
        target_entity_id=relationship.target_entity_id,
        relationship_type=relationship.relationship_type,
        description=relationship.description,
        strength=relationship.strength,
        start_date=relationship.start_date,
        end_date=relationship.end_date,
        metadata=relationship.metadata,
        source=relationship.source
    )
    return {"id": rel_id, "message": "Relationship created successfully"}


@router.get("/{entity_id}/relationships")
@handle_api_errors("get relationships")
async def get_relationships_endpoint(
    entity_id: str,
    direction: str = Query("both", description="'outgoing', 'incoming', or 'both'")
):
    """Get all relationships for an entity."""
    relationships = get_entity_relationships(entity_id, direction)
    return {"relationships": relationships, "count": len(relationships)}


# =============================================================================
# Notes Endpoints
# =============================================================================

@router.post("/{entity_id}/notes", status_code=201)
@handle_api_errors("add note")
async def add_note_endpoint(entity_id: str, note: NoteCreate):
    """Add a note to an entity."""
    note_id = add_entity_note(
        entity_id=entity_id,
        note_type=note.note_type,
        content=note.content,
        importance=note.importance,
        valid_until=note.valid_until,
        source=note.source
    )
    return {"id": note_id, "message": "Note added successfully"}


@router.get("/{entity_id}/notes")
@handle_api_errors("get notes")
async def get_notes_endpoint(
    entity_id: str,
    note_type: Optional[str] = Query(None),
    include_expired: bool = Query(False)
):
    """Get notes for an entity."""
    notes = get_entity_notes(entity_id, note_type, include_expired)
    return {"notes": notes, "count": len(notes)}
