"""
Athena Server v2 - Neon Database Connection
PostgreSQL connection using psycopg v3 for Python 3.13 compatibility.
"""

import time
import logging
from contextlib import contextmanager
from typing import Optional, Generator

import psycopg
from psycopg.rows import dict_row

from config import settings

logger = logging.getLogger("athena.db")

# Connection pool settings
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds


def get_db_connection(max_retries: int = MAX_RETRIES) -> Optional[psycopg.Connection]:
    """
    Get a database connection with retry logic for Neon cold starts.
    
    Note: Do NOT use 'options' parameter with Neon pooler endpoint.
    PgBouncer does not support startup parameters like statement_timeout.
    
    Args:
        max_retries: Number of connection attempts
        
    Returns:
        Database connection or None if all retries fail
    """
    for attempt in range(max_retries):
        try:
            conn = psycopg.connect(
                settings.DATABASE_URL,
                connect_timeout=30
            )
            logger.debug(f"Database connection established (attempt {attempt + 1})")
            return conn
        except Exception as e:
            logger.warning(f"Database connection attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(RETRY_DELAY)
    
    logger.error("All database connection attempts failed")
    return None


@contextmanager
def db_cursor(dict_cursor: bool = True) -> Generator:
    """
    Context manager for database operations.
    
    Args:
        dict_cursor: If True, returns results as dictionaries
        
    Yields:
        Database cursor
    """
    conn = get_db_connection()
    if not conn:
        raise Exception("Could not establish database connection")
    
    try:
        row_factory = dict_row if dict_cursor else None
        cursor = conn.cursor(row_factory=row_factory)
        yield cursor
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Database operation failed: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


async def check_db_health() -> bool:
    """
    Check database connection health.
    
    Returns:
        True if database is accessible, False otherwise
    """
    for attempt in range(3):
        try:
            conn = psycopg.connect(
                settings.DATABASE_URL,
                connect_timeout=30
            )
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            conn.close()
            logger.debug(f"Database health check passed (attempt {attempt + 1})")
            return True
        except Exception as e:
            logger.warning(f"Database health check attempt {attempt + 1} failed: {e}")
            if attempt < 2:
                time.sleep(5)
    
    logger.error("All database health check attempts failed")
    return False


# Query helpers - Updated to match actual Neon schema

def get_recent_observations(limit: int = 50, source_type: str = None) -> list:
    """Get recent observations from the database."""
    with db_cursor() as cursor:
        if source_type:
            cursor.execute("""
                SELECT * FROM observations 
                WHERE source_type = %s
                ORDER BY observed_at DESC 
                LIMIT %s
            """, (source_type, limit))
        else:
            cursor.execute("""
                SELECT * FROM observations 
                ORDER BY observed_at DESC 
                LIMIT %s
            """, (limit,))
        return cursor.fetchall()


def get_unprocessed_observations() -> list:
    """Get observations not yet processed by pattern detection."""
    with db_cursor() as cursor:
        cursor.execute("""
            SELECT * FROM observations 
            WHERE processed_tier_2 = FALSE OR processed_tier_2 IS NULL
            ORDER BY observed_at DESC
        """)
        return cursor.fetchall()


def get_recent_patterns(limit: int = 20) -> list:
    """Get recent patterns from the database."""
    with db_cursor() as cursor:
        cursor.execute("""
            SELECT * FROM patterns 
            ORDER BY detected_at DESC 
            LIMIT %s
        """, (limit,))
        return cursor.fetchall()


def get_latest_synthesis() -> Optional[dict]:
    """Get the most recent synthesis."""
    with db_cursor() as cursor:
        cursor.execute("""
            SELECT * FROM synthesis_memory 
            ORDER BY created_at DESC 
            LIMIT 1
        """)
        return cursor.fetchone()


def get_pending_drafts() -> list:
    """Get email drafts pending review."""
    with db_cursor() as cursor:
        cursor.execute("""
            SELECT * FROM email_drafts 
            WHERE status = 'pending_review'
            ORDER BY created_at DESC
        """)
        return cursor.fetchall()


def get_canonical_memory() -> list:
    """Get all canonical memory entries."""
    with db_cursor() as cursor:
        cursor.execute("""
            SELECT * FROM canonical_memory 
            WHERE active = TRUE
            ORDER BY category, created_at DESC
        """)
        return cursor.fetchall()


def get_vip_contacts() -> list:
    """Get VIP contacts from canonical memory."""
    with db_cursor() as cursor:
        cursor.execute("""
            SELECT * FROM canonical_memory 
            WHERE category = 'vip_contact' AND active = TRUE
        """)
        return cursor.fetchall()


def store_observation(observation: dict) -> str:
    """
    Store a new observation and return its ID.
    Schema: source_type, source_id, category, priority, requires_action,
            title, summary, raw_metadata, observed_at
    """
    with db_cursor() as cursor:
        cursor.execute("""
            INSERT INTO observations (
                source_type, source_id, observed_at, category, priority,
                requires_action, title, summary, raw_metadata
            ) VALUES (
                %(source_type)s, %(source_id)s, %(observed_at)s, %(category)s, %(priority)s,
                %(requires_action)s, %(title)s, %(summary)s, %(raw_metadata)s
            )
            ON CONFLICT (source_type, source_id) DO UPDATE SET
                category = EXCLUDED.category,
                priority = EXCLUDED.priority,
                summary = EXCLUDED.summary,
                requires_action = EXCLUDED.requires_action
            RETURNING id
        """, observation)
        return str(cursor.fetchone()['id'])


def mark_observations_processed_tier2(observation_ids: list):
    """Mark observations as processed by Tier 2."""
    with db_cursor() as cursor:
        cursor.execute("""
            UPDATE observations 
            SET processed_tier_2 = TRUE 
            WHERE id = ANY(%s::uuid[])
        """, (observation_ids,))


def store_pattern(pattern: dict) -> str:
    """
    Store a new pattern and return its ID.
    Schema: pattern_type, pattern_name, description, confidence, evidence,
            observation_ids, status, detected_at
    """
    with db_cursor() as cursor:
        cursor.execute("""
            INSERT INTO patterns (
                pattern_type, pattern_name, description, confidence, 
                observation_ids, detected_at, evidence
            ) VALUES (
                %(pattern_type)s, %(pattern_name)s, %(description)s, %(confidence)s,
                %(observation_ids)s::uuid[], %(detected_at)s, %(evidence)s
            )
            RETURNING id
        """, pattern)
        return str(cursor.fetchone()['id'])


def store_synthesis(synthesis: dict) -> str:
    """
    Store a new synthesis and return its ID.
    Schema: synthesis_type, synthesis_number, observations_count, patterns_count,
            executive_summary, key_insights, questions_for_bradley, 
            suggested_memory_updates, action_recommendations
    """
    with db_cursor() as cursor:
        cursor.execute("""
            INSERT INTO synthesis_memory (
                synthesis_type, synthesis_number, observations_count, patterns_count,
                executive_summary, key_insights, questions_for_bradley,
                suggested_memory_updates, action_recommendations, created_at
            ) VALUES (
                %(synthesis_type)s, %(synthesis_number)s, %(observations_count)s, %(patterns_count)s,
                %(executive_summary)s, %(key_insights)s, %(questions_for_bradley)s,
                %(suggested_memory_updates)s, %(action_recommendations)s, %(created_at)s
            )
            RETURNING id
        """, synthesis)
        return str(cursor.fetchone()['id'])


def store_email_draft(draft: dict) -> str:
    """Store a new email draft and return its ID."""
    with db_cursor() as cursor:
        cursor.execute("""
            INSERT INTO email_drafts (
                observation_id, to_address, subject, body, reasoning, status
            ) VALUES (
                %(observation_id)s, %(to_address)s, %(subject)s, %(body)s, 
                %(reasoning)s, %(status)s
            )
            RETURNING id
        """, draft)
        return str(cursor.fetchone()['id'])


def update_deep_learning_progress(progress: dict) -> str:
    """Store deep learning progress entry."""
    with db_cursor() as cursor:
        cursor.execute("""
            INSERT INTO deep_learning_progress (
                source_type, source_id, source_title, content_length,
                reading_time_seconds, insights_count, read_at
            ) VALUES (
                %(source_type)s, %(source_id)s, %(source_title)s, %(content_length)s,
                %(reading_time_seconds)s, %(insights_count)s, %(read_at)s
            )
            RETURNING id
        """, progress)
        return str(cursor.fetchone()['id'])
