"""
Athena Server v2 - Entity API Routes

API endpoints for managing entities (people, organizations, projects)
in the knowledge graph.
"""

import logging
from typing import Optional, List
from datetime import datetime, date

from fastapi import APIRouter, HTTPException, Depends, Query
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
async def create_entity_endpoint(entity: EntityCreate):
    """Create a new entity."""
    try:
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
    except Exception as e:
        logger.error(f"Failed to create entity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def list_entities(
    query: Optional[str] = Query(None, description="Search query"),
    entity_type: Optional[str] = Query(None, description="Filter by type"),
    access_tier: Optional[str] = Query(None, description="Filter by access tier"),
    limit: int = Query(20, ge=1, le=100)
):
    """Search and list entities."""
    try:
        entities = search_entities(
            query=query,
            entity_type=entity_type,
            access_tier=access_tier,
            limit=limit
        )
        return {"entities": entities, "count": len(entities)}
    except Exception as e:
        logger.error(f"Failed to list entities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vip")
async def list_vip_entities():
    """Get all VIP entities."""
    try:
        entities = get_vip_entities()
        return {"entities": entities, "count": len(entities)}
    except Exception as e:
        logger.error(f"Failed to get VIP entities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/by-name/{name}")
async def get_entity_by_name_endpoint(
    name: str,
    entity_type: Optional[str] = Query(None)
):
    """Get an entity by name (case-insensitive)."""
    try:
        entity = get_entity_by_name(name, entity_type)
        if not entity:
            raise HTTPException(status_code=404, detail="Entity not found")
        return entity
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get entity by name: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/type/{entity_type}")
async def list_entities_by_type(entity_type: str):
    """Get all entities of a specific type."""
    try:
        entities = get_entities_by_type(entity_type)
        return {"entities": entities, "count": len(entities)}
    except Exception as e:
        logger.error(f"Failed to list entities by type: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{entity_id}")
async def get_entity_endpoint(entity_id: str):
    """Get an entity by ID."""
    try:
        entity = get_entity(entity_id)
        if not entity:
            raise HTTPException(status_code=404, detail="Entity not found")
        return entity
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get entity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{entity_id}/context")
async def get_entity_context_endpoint(entity_id: str):
    """Get complete context for an entity including relationships and notes."""
    try:
        context = get_entity_context(entity_id)
        if not context:
            raise HTTPException(status_code=404, detail="Entity not found")
        return context
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get entity context: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{entity_id}")
async def update_entity_endpoint(entity_id: str, entity: EntityUpdate):
    """Update an entity."""
    try:
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
            raise HTTPException(status_code=404, detail="Entity not found or no changes")
        return {"message": "Entity updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update entity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{entity_id}")
async def delete_entity_endpoint(entity_id: str, hard_delete: bool = Query(False)):
    """Delete an entity (soft delete by default)."""
    try:
        success = delete_entity(entity_id, soft_delete=not hard_delete)
        if not success:
            raise HTTPException(status_code=404, detail="Entity not found")
        return {"message": "Entity deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete entity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Relationship Endpoints
# =============================================================================

@router.post("/relationships", status_code=201)
async def create_relationship_endpoint(relationship: RelationshipCreate):
    """Create a relationship between two entities."""
    try:
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
    except Exception as e:
        logger.error(f"Failed to create relationship: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{entity_id}/relationships")
async def get_relationships_endpoint(
    entity_id: str,
    direction: str = Query("both", description="'outgoing', 'incoming', or 'both'")
):
    """Get all relationships for an entity."""
    try:
        relationships = get_entity_relationships(entity_id, direction)
        return {"relationships": relationships, "count": len(relationships)}
    except Exception as e:
        logger.error(f"Failed to get relationships: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Notes Endpoints
# =============================================================================

@router.post("/{entity_id}/notes", status_code=201)
async def add_note_endpoint(entity_id: str, note: NoteCreate):
    """Add a note to an entity."""
    try:
        note_id = add_entity_note(
            entity_id=entity_id,
            note_type=note.note_type,
            content=note.content,
            importance=note.importance,
            valid_until=note.valid_until,
            source=note.source
        )
        return {"id": note_id, "message": "Note added successfully"}
    except Exception as e:
        logger.error(f"Failed to add note: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{entity_id}/notes")
async def get_notes_endpoint(
    entity_id: str,
    note_type: Optional[str] = Query(None),
    include_expired: bool = Query(False)
):
    """Get notes for an entity."""
    try:
        notes = get_entity_notes(entity_id, note_type, include_expired)
        return {"notes": notes, "count": len(notes)}
    except Exception as e:
        logger.error(f"Failed to get notes: {e}")
        raise HTTPException(status_code=500, detail=str(e))
