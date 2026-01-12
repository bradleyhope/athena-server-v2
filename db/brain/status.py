"""
Athena Brain - Status Module

Brain status tracking and Notion sync logging.
"""

import logging
import json
from typing import Optional, List, Dict, Any

from db.neon import db_cursor

logger = logging.getLogger("athena.db.brain.status")


# =============================================================================
# BRAIN STATUS
# =============================================================================

def get_brain_status() -> Optional[Dict]:
    """Get current brain status."""
    with db_cursor() as cursor:
        cursor.execute("SELECT * FROM brain_status LIMIT 1")
        return cursor.fetchone()


def update_brain_status(status: str = None, config: Dict = None) -> bool:
    """Update brain status."""
    with db_cursor() as cursor:
        updates = []
        params = []

        if status:
            updates.append("status = %s")
            params.append(status)
        if config:
            updates.append("config = %s")
            params.append(json.dumps(config))

        if not updates:
            return False

        updates.append("updated_at = NOW()")
        query = f"UPDATE brain_status SET {', '.join(updates)}"
        cursor.execute(query, params)
        return True


def record_synthesis_time() -> bool:
    """Record that a synthesis was performed."""
    with db_cursor() as cursor:
        cursor.execute("UPDATE brain_status SET last_synthesis_at = NOW()")
        return True


def record_evolution_time() -> bool:
    """Record that evolution engine ran."""
    with db_cursor() as cursor:
        cursor.execute("UPDATE brain_status SET last_evolution_at = NOW()")
        return True


def record_notion_sync_time() -> bool:
    """Record that Notion sync was performed."""
    with db_cursor() as cursor:
        cursor.execute("UPDATE brain_status SET last_notion_sync_at = NOW()")
        return True


# =============================================================================
# NOTION SYNC
# =============================================================================

def log_notion_sync(
    source_table: str,
    source_id: str,
    sync_type: str,
    notion_page_id: str = None,
    notion_database_id: str = None
) -> str:
    """Log a Notion sync operation."""
    with db_cursor() as cursor:
        cursor.execute("""
            INSERT INTO notion_sync_log (
                source_table, source_id, sync_type, notion_page_id, notion_database_id
            ) VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (source_table, source_id, sync_type, notion_page_id, notion_database_id))
        return str(cursor.fetchone()['id'])


def update_notion_sync_status(sync_id: str, status: str, error_message: str = None) -> bool:
    """Update Notion sync status."""
    with db_cursor() as cursor:
        cursor.execute("""
            UPDATE notion_sync_log SET
                sync_status = %s,
                error_message = %s,
                synced_at = CASE WHEN %s = 'success' THEN NOW() ELSE synced_at END
            WHERE id = %s
        """, (status, error_message, status, sync_id))
        return cursor.rowcount > 0


def get_pending_notion_syncs() -> List[Dict]:
    """Get pending Notion sync operations."""
    with db_cursor() as cursor:
        cursor.execute("""
            SELECT * FROM notion_sync_log
            WHERE sync_status = 'pending'
            ORDER BY created_at
        """)
        return cursor.fetchall()
