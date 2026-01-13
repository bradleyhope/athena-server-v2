"""
Athena Brain - Composite Queries

Complex queries that span multiple layers, plus continuous state context,
daily impressions, and entity management.
"""

import logging
import json
from typing import Optional, List, Dict, Any
from datetime import datetime, date

from db.neon import db_cursor
from db.brain.identity import get_core_identity, get_boundaries, get_values
from db.brain.knowledge import get_workflows
from db.brain.state import get_pending_actions, get_session_state
from db.brain.evolution import get_evolution_proposals
from db.brain.status import get_brain_status

logger = logging.getLogger("athena.db.brain.composite")


# =============================================================================
# COMPOSITE QUERIES
# =============================================================================

def get_full_brain_context() -> Dict[str, Any]:
    """
    Get the complete brain context for a Manus session.
    This is the primary method for loading Athena's brain into a session.

    Returns:
        Dictionary containing all brain layers
    """
    return {
        'identity': get_core_identity(),
        'boundaries': get_boundaries(),
        'values': get_values(),
        'workflows': get_workflows(),
        'status': get_brain_status(),
        'pending_actions': get_pending_actions(),
        'evolution_proposals': get_evolution_proposals()
    }


def get_session_brief(session_type: str) -> Dict[str, Any]:
    """
    Get a brief for starting a specific session type.

    Args:
        session_type: Type of session (athena_thinking, agenda_workspace, etc.)

    Returns:
        Dictionary with relevant context for the session
    """
    identity = get_core_identity()
    boundaries = get_boundaries(active_only=True)
    values = get_values()
    status = get_brain_status()
    recent_state = get_session_state(session_type)

    return {
        'identity': {k: v['value'] for k, v in identity.items()},
        'boundaries': [{'type': b['boundary_type'], 'category': b['category'], 'rule': b['rule']} for b in boundaries],
        'values': [{'priority': v['priority'], 'name': v['value_name'], 'description': v['description']} for v in values],
        'status': status['status'] if status else 'unknown',
        'handoff_context': recent_state['handoff_context'] if recent_state else None,
        'pending_actions_count': len(get_pending_actions()),
        'evolution_proposals_count': len(get_evolution_proposals())
    }


# =============================================================================
# DAILY IMPRESSIONS
# =============================================================================

def store_daily_impression(
    impression_date: date,
    category: str,
    content: str,
    confidence: float = 0.8,
    source_data: Dict = None
) -> str:
    """
    Store a daily impression in synthesis_memory.

    Args:
        impression_date: Date of the impression
        category: relationship|opportunity|risk|theme
        content: The impression text
        confidence: Confidence score 0.0-1.0
        source_data: Source emails/events that led to this impression

    Returns:
        Memory ID
    """
    with db_cursor() as cursor:
        cursor.execute("""
            INSERT INTO synthesis_memory (
                synthesis_type, content, confidence_score,
                source_observations, created_at
            ) VALUES (%s, %s, %s, %s, NOW())
            RETURNING id
        """, (
            f"impression_{category}",
            json.dumps({
                "date": impression_date.isoformat(),
                "category": category,
                "content": content,
                "confidence": confidence
            }),
            confidence,
            json.dumps(source_data) if source_data else None
        ))
        result = cursor.fetchone()
        logger.info(f"Stored daily impression: {category}")
        return str(result['id'])


def store_daily_impressions_batch(impression_date: date, impressions: List[Dict]) -> List[str]:
    """Store multiple impressions at once."""
    ids = []
    for imp in impressions:
        imp_id = store_daily_impression(
            impression_date=impression_date,
            category=imp.get("category", "theme"),
            content=imp.get("content", ""),
            confidence=imp.get("confidence", 0.8),
            source_data=imp.get("sources")
        )
        ids.append(imp_id)
    return ids


def get_recent_impressions(days: int = 7, category: str = None) -> List[Dict]:
    """Get recent impressions from synthesis_memory."""
    with db_cursor() as cursor:
        query = """
            SELECT id, content, confidence_score, created_at
            FROM synthesis_memory
            WHERE synthesis_type LIKE 'impression_%'
            AND created_at > NOW() - INTERVAL '%s days'
        """
        params = [days]

        if category:
            query += " AND synthesis_type = %s"
            params.append(f"impression_{category}")

        query += " ORDER BY created_at DESC"
        cursor.execute(query, params)
        rows = cursor.fetchall()

        impressions = []
        for row in rows:
            content = json.loads(row['content']) if isinstance(row['content'], str) else row['content']
            impressions.append({
                "id": str(row['id']),
                "date": content.get("date"),
                "category": content.get("category"),
                "content": content.get("content"),
                "confidence": row['confidence_score'],
                "created_at": row['created_at'].isoformat() if row['created_at'] else None
            })
        return impressions


def get_todays_impressions() -> List[Dict]:
    """Get impressions from today."""
    today = date.today()
    with db_cursor() as cursor:
        cursor.execute("""
            SELECT id, content, confidence_score, created_at
            FROM synthesis_memory
            WHERE synthesis_type LIKE 'impression_%'
            AND DATE(created_at) = %s
            ORDER BY created_at DESC
        """, (today,))
        rows = cursor.fetchall()

        impressions = []
        for row in rows:
            content = json.loads(row['content']) if isinstance(row['content'], str) else row['content']
            impressions.append({
                "id": str(row['id']),
                "category": content.get("category"),
                "content": content.get("content"),
                "confidence": row['confidence_score']
            })
        return impressions


# =============================================================================
# CONTINUOUS STATE CONTEXT
# =============================================================================

def get_recent_sessions(days: int = 7) -> List[Dict]:
    """Get recent Athena sessions for continuity."""
    with db_cursor() as cursor:
        cursor.execute("""
            SELECT session_type, session_date, manus_task_id, manus_task_url, updated_at
            FROM active_sessions
            WHERE session_date >= CURRENT_DATE - INTERVAL '%s days'
            ORDER BY session_date DESC, updated_at DESC
        """, (days,))
        return [
            {
                "type": row['session_type'],
                "date": row['session_date'].strftime("%Y-%m-%d") if row['session_date'] else None,
                "task_id": row['manus_task_id'],
                "url": row['manus_task_url']
            }
            for row in cursor.fetchall()
        ]


def get_recent_observations(limit: int = 10) -> List[Dict]:
    """Get recent observations for context."""
    with db_cursor() as cursor:
        cursor.execute("""
            SELECT
                category,
                COALESCE(summary, title) AS content,
                source_type AS source,
                1.0 AS confidence,
                observed_at AS created_at
            FROM observations
            ORDER BY observed_at DESC
            LIMIT %s
        """, (limit,))
        return [
            {
                "category": row['category'],
                "content": row['content'][:150] if row['content'] else None,
                "source": row['source'],
                "confidence": row['confidence'],
                "when": row['created_at'].strftime("%Y-%m-%d %H:%M") if row['created_at'] else None
            }
            for row in cursor.fetchall()
        ]


def get_recent_patterns(limit: int = 5) -> List[Dict]:
    """Get recent detected patterns."""
    with db_cursor() as cursor:
        cursor.execute("""
            SELECT pattern_type, description, confidence, evidence_count, detected_at
            FROM patterns
            ORDER BY detected_at DESC
            LIMIT %s
        """, (limit,))
        return [
            {
                "type": row['pattern_type'],
                "description": row['description'][:150] if row['description'] else None,
                "confidence": row['confidence'],
                "evidence_count": row['evidence_count'],
                "when": row['detected_at'].strftime("%Y-%m-%d") if row['detected_at'] else None
            }
            for row in cursor.fetchall()
        ]


def get_recent_synthesis(limit: int = 3) -> List[Dict]:
    """Get recent synthesis/conclusions."""
    with db_cursor() as cursor:
        cursor.execute("""
            SELECT synthesis_date, executive_summary, key_insights, synthesis_number
            FROM synthesis_memory
            WHERE executive_summary IS NOT NULL
            ORDER BY synthesis_date DESC
            LIMIT %s
        """, (limit,))
        return [
            {
                "date": row['synthesis_date'].strftime("%Y-%m-%d") if row['synthesis_date'] else None,
                "summary": row['executive_summary'][:200] if row['executive_summary'] else None,
                "insights": row['key_insights'][:200] if row['key_insights'] else None,
                "number": row['synthesis_number']
            }
            for row in cursor.fetchall()
        ]


def get_continuous_state_context() -> Dict[str, Any]:
    """
    Get Athena's complete continuous state for self-awareness.
    This is the main function to call for building the system prompt.
    """
    return {
        "recent_sessions": get_recent_sessions(days=7),
        "recent_observations": get_recent_observations(limit=10),
        "recent_patterns": get_recent_patterns(limit=5),
        "recent_synthesis": get_recent_synthesis(limit=3),
        "recent_impressions": get_recent_impressions(limit=5),
    }


# =============================================================================
# ENTITIES - Knowledge Graph
# =============================================================================

def create_entity(
    entity_type: str,
    name: str,
    description: str = None,
    aliases: List[str] = None,
    metadata: Dict = None,
    access_tier: str = "default",
    source: str = None,
    confidence: float = 1.0
) -> str:
    """Create a new entity in the knowledge graph."""
    with db_cursor() as cursor:
        cursor.execute("""
            INSERT INTO entities (entity_type, name, canonical_name, description, aliases, metadata, access_tier, source, confidence)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            entity_type, name, name, description,
            aliases or [], json.dumps(metadata or {}),
            access_tier, source, confidence
        ))
        entity_id = str(cursor.fetchone()['id'])
        logger.info(f"Created entity: {entity_type}/{name} ({entity_id})")
        return entity_id


def get_entity(entity_id: str) -> Optional[Dict]:
    """Get an entity by ID."""
    with db_cursor() as cursor:
        cursor.execute("SELECT * FROM entities WHERE id = %s", (entity_id,))
        return cursor.fetchone()


def get_entity_by_name(name: str, entity_type: str = None) -> Optional[Dict]:
    """Get an entity by name (case-insensitive) or alias."""
    with db_cursor() as cursor:
        query = """
            SELECT * FROM entities
            WHERE active = TRUE
            AND (
                LOWER(name) = LOWER(%s)
                OR aliases @> %s::jsonb
            )
        """
        params = [name, json.dumps([name.lower()])]

        if entity_type:
            query += " AND entity_type = %s"
            params.append(entity_type)

        query += " ORDER BY confidence DESC LIMIT 1"
        cursor.execute(query, params)
        return cursor.fetchone()


def search_entities(
    query: str = None,
    entity_type: str = None,
    access_tier: str = None,
    limit: int = 20
) -> List[Dict]:
    """Search for entities."""
    with db_cursor() as cursor:
        sql = "SELECT * FROM entities WHERE active = TRUE"
        params = []

        if query:
            sql += " AND to_tsvector('english', name || ' ' || COALESCE(description, '')) @@ plainto_tsquery('english', %s)"
            params.append(query)

        if entity_type:
            sql += " AND entity_type = %s"
            params.append(entity_type)

        if access_tier:
            sql += " AND access_tier = %s"
            params.append(access_tier)

        sql += " ORDER BY confidence DESC, name LIMIT %s"
        params.append(limit)

        cursor.execute(sql, params)
        return cursor.fetchall()


def get_entities_by_type(entity_type: str, active_only: bool = True) -> List[Dict]:
    """Get all entities of a specific type."""
    with db_cursor() as cursor:
        query = "SELECT * FROM entities WHERE entity_type = %s"
        params = [entity_type]

        if active_only:
            query += " AND active = TRUE"

        query += " ORDER BY name"
        cursor.execute(query, params)
        return cursor.fetchall()


def get_vip_entities() -> List[Dict]:
    """Get all VIP entities."""
    with db_cursor() as cursor:
        cursor.execute("""
            SELECT * FROM entities
            WHERE access_tier = 'vip' AND active = TRUE
            ORDER BY name
        """)
        return cursor.fetchall()


def update_entity(
    entity_id: str,
    name: str = None,
    description: str = None,
    aliases: List[str] = None,
    metadata: Dict = None,
    access_tier: str = None,
    confidence: float = None
) -> bool:
    """Update an entity."""
    updates = []
    params = []

    if name is not None:
        updates.append("name = %s")
        params.append(name)
    if description is not None:
        updates.append("description = %s")
        params.append(description)
    if aliases is not None:
        updates.append("aliases = %s")
        params.append(json.dumps(aliases))
    if metadata is not None:
        updates.append("metadata = %s")
        params.append(json.dumps(metadata))
    if access_tier is not None:
        updates.append("access_tier = %s")
        params.append(access_tier)
    if confidence is not None:
        updates.append("confidence = %s")
        params.append(confidence)

    if not updates:
        return False

    updates.append("updated_at = NOW()")
    params.append(entity_id)

    with db_cursor() as cursor:
        cursor.execute(f"""
            UPDATE entities SET {', '.join(updates)}
            WHERE id = %s
        """, params)
        return cursor.rowcount > 0


def delete_entity(entity_id: str, soft_delete: bool = True) -> bool:
    """Delete an entity."""
    with db_cursor() as cursor:
        if soft_delete:
            cursor.execute("UPDATE entities SET active = FALSE, updated_at = NOW() WHERE id = %s", (entity_id,))
        else:
            cursor.execute("DELETE FROM entities WHERE id = %s", (entity_id,))
        return cursor.rowcount > 0


def create_relationship(
    source_entity_id: str,
    target_entity_id: str,
    relationship_type: str,
    description: str = None,
    strength: float = 1.0,
    start_date: date = None,
    end_date: date = None,
    metadata: Dict = None,
    source: str = None
) -> str:
    """Create a relationship between two entities."""
    with db_cursor() as cursor:
        cursor.execute("""
            INSERT INTO entity_relationships
            (source_entity_id, target_entity_id, relationship_type, evidence, confidence)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (source_entity_id, target_entity_id, relationship_type, description, strength))
        return str(cursor.fetchone()['id'])


def get_entity_relationships(entity_id: str, direction: str = "both") -> List[Dict]:
    """Get all relationships for an entity."""
    with db_cursor() as cursor:
        if direction == "outgoing":
            cursor.execute("""
                SELECT r.*, e.name as target_name, e.entity_type as target_type
                FROM entity_relationships r
                JOIN entities e ON r.target_entity_id = e.id
                WHERE r.source_entity_id = %s AND r.active = TRUE
                ORDER BY r.strength DESC
            """, (entity_id,))
        elif direction == "incoming":
            cursor.execute("""
                SELECT r.*, e.name as source_name, e.entity_type as source_type
                FROM entity_relationships r
                JOIN entities e ON r.source_entity_id = e.id
                WHERE r.target_entity_id = %s AND r.active = TRUE
                ORDER BY r.strength DESC
            """, (entity_id,))
        else:
            cursor.execute("""
                SELECT r.*,
                    se.name as source_name, se.entity_type as source_type,
                    te.name as target_name, te.entity_type as target_type
                FROM entity_relationships r
                JOIN entities se ON r.source_entity_id = se.id
                JOIN entities te ON r.target_entity_id = te.id
                WHERE (r.source_entity_id = %s OR r.target_entity_id = %s) AND r.active = TRUE
                ORDER BY r.strength DESC
            """, (entity_id, entity_id))

        return cursor.fetchall()


def add_entity_note(
    entity_id: str,
    note_type: str,
    content: str,
    importance: str = "normal",
    valid_until: datetime = None,
    source: str = None
) -> str:
    """Add a note to an entity."""
    with db_cursor() as cursor:
        cursor.execute("""
            INSERT INTO entity_notes (entity_id, note_type, content, importance, valid_until, source)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (entity_id, note_type, content, importance, valid_until, source))
        return str(cursor.fetchone()['id'])


def get_entity_notes(entity_id: str, note_type: str = None, include_expired: bool = False) -> List[Dict]:
    """Get notes for an entity."""
    with db_cursor() as cursor:
        query = "SELECT * FROM entity_notes WHERE entity_id = %s"
        params = [entity_id]

        if note_type:
            query += " AND note_type = %s"
            params.append(note_type)

        if not include_expired:
            query += " AND (valid_until IS NULL OR valid_until > NOW())"

        query += " ORDER BY importance DESC, created_at DESC"
        cursor.execute(query, params)
        return cursor.fetchall()


def get_entity_context(entity_id: str) -> Dict[str, Any]:
    """Get complete context for an entity including relationships and notes."""
    entity = get_entity(entity_id)
    if not entity:
        return None

    return {
        "entity": entity,
        "relationships": get_entity_relationships(entity_id),
        "notes": get_entity_notes(entity_id),
    }
