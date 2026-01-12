"""
Athena Brain - Knowledge Layer (Layer 2)

Workflows, preferences, and procedural knowledge.
"""

import logging
import json
from typing import Optional, List, Dict, Any

from db.neon import db_cursor

logger = logging.getLogger("athena.db.brain.knowledge")


# =============================================================================
# WORKFLOWS
# =============================================================================

def get_workflows(enabled_only: bool = True) -> List[Dict]:
    """Get all workflows."""
    with db_cursor() as cursor:
        query = "SELECT * FROM workflows"
        if enabled_only:
            query += " WHERE enabled = TRUE"
        query += " ORDER BY workflow_name"
        cursor.execute(query)
        return cursor.fetchall()


def get_workflow(workflow_name: str) -> Optional[Dict]:
    """Get a specific workflow by name."""
    with db_cursor() as cursor:
        cursor.execute("SELECT * FROM workflows WHERE workflow_name = %s", (workflow_name,))
        return cursor.fetchone()


def update_workflow_execution(workflow_name: str, success: bool) -> bool:
    """
    Update workflow execution statistics.

    Args:
        workflow_name: Name of the workflow
        success: Whether the execution was successful

    Returns:
        True if updated
    """
    with db_cursor() as cursor:
        cursor.execute("""
            UPDATE workflows SET
                execution_count = execution_count + 1,
                last_executed_at = NOW(),
                success_rate = (success_rate * execution_count + %s) / (execution_count + 1)
            WHERE workflow_name = %s
        """, (1.0 if success else 0.0, workflow_name))
        return True


def create_workflow(
    workflow_name: str,
    description: str,
    trigger_type: str,
    trigger_config: Dict,
    steps: List[Dict],
    requires_approval: bool = False
) -> str:
    """Create a new workflow and return its ID."""
    with db_cursor() as cursor:
        cursor.execute("""
            INSERT INTO workflows (workflow_name, description, trigger_type, trigger_config, steps, requires_approval)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (workflow_name, description, trigger_type, json.dumps(trigger_config), json.dumps(steps), requires_approval))
        return str(cursor.fetchone()['id'])


# =============================================================================
# PREFERENCES
# =============================================================================

def get_preferences(category: str = None) -> List[Dict]:
    """Get all preferences, optionally filtered by category."""
    with db_cursor() as cursor:
        if category:
            cursor.execute("""
                SELECT id, category, key, value, confidence, source, learned_from, created_at, updated_at
                FROM preferences
                WHERE category = %s
                ORDER BY category, confidence DESC
            """, (category,))
        else:
            cursor.execute("""
                SELECT id, category, key, value, confidence, source, learned_from, created_at, updated_at
                FROM preferences
                ORDER BY category, confidence DESC
            """)
        rows = cursor.fetchall()
        return [
            {
                "id": str(row['id']),
                "category": row['category'],
                "key": row['key'],
                "value": row['value'],
                "confidence": float(row['confidence']) if row['confidence'] else 0.5,
                "source": row['source'],
                "learned_from": row['learned_from'],
                "created_at": row['created_at'].isoformat() if row['created_at'] else None,
                "updated_at": row['updated_at'].isoformat() if row['updated_at'] else None,
            }
            for row in rows
        ]


def get_preference(category: str, key: str) -> Optional[Dict]:
    """Get a specific preference by category and key."""
    with db_cursor() as cursor:
        cursor.execute("""
            SELECT id, category, key, value, confidence, source, learned_from, created_at, updated_at
            FROM preferences
            WHERE category = %s AND key = %s
        """, (category, key))
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "id": str(row['id']),
            "category": row['category'],
            "key": row['key'],
            "value": row['value'],
            "confidence": float(row['confidence']) if row['confidence'] else 0.5,
            "source": row['source'],
            "learned_from": row['learned_from'],
            "created_at": row['created_at'].isoformat() if row['created_at'] else None,
            "updated_at": row['updated_at'].isoformat() if row['updated_at'] else None,
        }


def set_preference(category: str, key: str, value: str, confidence: float = 0.5, source: str = "manual", learned_from: str = None) -> str:
    """Create or update a preference."""
    with db_cursor() as cursor:
        cursor.execute("""
            INSERT INTO preferences (category, key, value, confidence, source, learned_from)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (category, key) DO UPDATE SET
                value = EXCLUDED.value,
                confidence = EXCLUDED.confidence,
                source = EXCLUDED.source,
                learned_from = EXCLUDED.learned_from,
                updated_at = NOW()
            RETURNING id
        """, (category, key, value, confidence, source, learned_from))
        return str(cursor.fetchone()['id'])
