"""
Athena Brain - Identity Layer (Layer 1)

Core identity values, boundaries, and values that define who Athena is.
"""

import logging
import json
from typing import Optional, List, Dict, Any

from db.neon import db_cursor

logger = logging.getLogger("athena.db.brain.identity")


def get_core_identity() -> Dict[str, Any]:
    """
    Get all core identity values as a dictionary.

    Returns:
        Dictionary of identity key-value pairs
    """
    with db_cursor() as cursor:
        cursor.execute("SELECT key, value, immutable FROM core_identity")
        rows = cursor.fetchall()
        return {row['key']: {'value': row['value'], 'immutable': row['immutable']} for row in rows}


def get_identity_value(key: str) -> Optional[Any]:
    """Get a specific identity value."""
    with db_cursor() as cursor:
        cursor.execute("SELECT value FROM core_identity WHERE key = %s", (key,))
        row = cursor.fetchone()
        return row['value'] if row else None


def update_identity_value(key: str, value: Any, description: str = None) -> bool:
    """
    Update a mutable identity value.

    Args:
        key: Identity key to update
        value: New value (will be JSON serialized)
        description: Optional description update

    Returns:
        True if updated, False if immutable or not found
    """
    with db_cursor() as cursor:
        cursor.execute("SELECT immutable FROM core_identity WHERE key = %s", (key,))
        row = cursor.fetchone()
        if not row:
            logger.warning(f"Identity key not found: {key}")
            return False
        if row['immutable']:
            logger.warning(f"Cannot update immutable identity key: {key}")
            return False

        if description:
            cursor.execute("""
                UPDATE core_identity
                SET value = %s, description = %s, updated_at = NOW()
                WHERE key = %s
            """, (json.dumps(value), description, key))
        else:
            cursor.execute("""
                UPDATE core_identity
                SET value = %s, updated_at = NOW()
                WHERE key = %s
            """, (json.dumps(value), key))

        logger.info(f"Updated identity value: {key}")
        return True


def get_boundaries(boundary_type: str = None, active_only: bool = True) -> List[Dict]:
    """
    Get boundaries, optionally filtered by type.

    Args:
        boundary_type: Filter by 'hard', 'soft', or 'contextual'
        active_only: Only return active boundaries

    Returns:
        List of boundary dictionaries
    """
    with db_cursor() as cursor:
        query = "SELECT * FROM boundaries WHERE 1=1"
        params = []

        if active_only:
            query += " AND active = TRUE"
        if boundary_type:
            query += " AND boundary_type = %s"
            params.append(boundary_type)

        query += " ORDER BY boundary_type, category"
        cursor.execute(query, params)
        return cursor.fetchall()


def check_boundary(category: str, action: str) -> Dict[str, Any]:
    """
    Check if an action is allowed based on boundaries.

    Args:
        category: Boundary category (e.g., 'email', 'financial')
        action: Description of the intended action

    Returns:
        Dictionary with 'allowed', 'requires_approval', 'boundary' keys
    """
    with db_cursor() as cursor:
        cursor.execute("""
            SELECT * FROM boundaries
            WHERE category = %s AND active = TRUE
            ORDER BY boundary_type
        """, (category,))
        boundaries = cursor.fetchall()

        if not boundaries:
            return {'allowed': True, 'requires_approval': False, 'boundary': None}

        for b in boundaries:
            if b['boundary_type'] == 'hard':
                return {
                    'allowed': False,
                    'requires_approval': True,
                    'boundary': b
                }

        for b in boundaries:
            if b['boundary_type'] == 'soft':
                return {
                    'allowed': True,
                    'requires_approval': b['requires_approval'],
                    'boundary': b
                }

        return {'allowed': True, 'requires_approval': False, 'boundary': boundaries[0]}


def get_values() -> List[Dict]:
    """Get all active values ordered by priority."""
    with db_cursor() as cursor:
        cursor.execute("""
            SELECT * FROM values
            WHERE active = TRUE
            ORDER BY priority
        """)
        return cursor.fetchall()
