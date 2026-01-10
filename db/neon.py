"""
Athena Server v2 - Neon Database Connection
PostgreSQL connection with retry logic for Neon cold starts.
"""

import asyncio
import logging
from contextlib import contextmanager
from typing import Optional, Generator

import psycopg2
from psycopg2.extras import RealDictCursor

from config import settings

logger = logging.getLogger("athena.db")

# Connection pool settings
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds


def get_db_connection(max_retries: int = MAX_RETRIES) -> Optional[psycopg2.extensions.connection]:
    """
    Get a database connection with retry logic for Neon cold starts.
    
    Args:
        max_retries: Number of connection attempts
        
    Returns:
        Database connection or None if all retries fail
    """
    for attempt in range(max_retries):
        try:
            conn = psycopg2.connect(
                settings.DATABASE_URL,
                connect_timeout=30,
                options="-c statement_timeout=30000"
            )
            logger.debug(f"Database connection established (attempt {attempt + 1})")
            return conn
        except Exception as e:
            logger.warning(f"Database connection attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                asyncio.sleep(RETRY_DELAY)
    
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
        cursor_factory = RealDictCursor if dict_cursor else None
        cursor = conn.cursor(cursor_factory=cursor_factory)
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
    try:
        conn = get_db_connection(max_retries=1)
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            conn.close()
            return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
    return False


# Query helpers

def get_recent_observations(limit: int = 50, source: str = None) -> list:
    """Get recent observations from the database."""
    with db_cursor() as cursor:
        if source:
            cursor.execute("""
                SELECT * FROM observations 
                WHERE source = %s
                ORDER BY observed_at DESC 
                LIMIT %s
            """, (source, limit))
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
            WHERE id NOT IN (
                SELECT DISTINCT unnest(observation_ids) FROM patterns
            )
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
            WHERE status = 'approved'
            ORDER BY category, created_at DESC
        """)
        return cursor.fetchall()


def get_vip_contacts() -> list:
    """Get VIP contacts from canonical memory."""
    with db_cursor() as cursor:
        cursor.execute("""
            SELECT * FROM canonical_memory 
            WHERE category = 'vip_contact' AND status = 'approved'
        """)
        return cursor.fetchall()


def store_observation(observation: dict) -> str:
    """Store a new observation and return its ID."""
    with db_cursor() as cursor:
        cursor.execute("""
            INSERT INTO observations (
                source, source_id, observed_at, category, priority,
                summary, raw_content, metadata
            ) VALUES (
                %(source)s, %(source_id)s, %(observed_at)s, %(category)s, %(priority)s,
                %(summary)s, %(raw_content)s, %(metadata)s
            )
            ON CONFLICT (source, source_id) DO UPDATE SET
                category = EXCLUDED.category,
                priority = EXCLUDED.priority,
                summary = EXCLUDED.summary
            RETURNING id
        """, observation)
        return cursor.fetchone()['id']


def store_pattern(pattern: dict) -> str:
    """Store a new pattern and return its ID."""
    with db_cursor() as cursor:
        cursor.execute("""
            INSERT INTO patterns (
                pattern_type, description, confidence, observation_ids,
                detected_at, metadata
            ) VALUES (
                %(pattern_type)s, %(description)s, %(confidence)s, %(observation_ids)s,
                %(detected_at)s, %(metadata)s
            )
            RETURNING id
        """, pattern)
        return cursor.fetchone()['id']


def store_synthesis(synthesis: dict) -> str:
    """Store a new synthesis and return its ID."""
    with db_cursor() as cursor:
        cursor.execute("""
            INSERT INTO synthesis_memory (
                synthesis_type, synthesis_number, executive_summary, key_insights,
                questions_for_user, memory_proposals, action_recommendations,
                observations_count, patterns_count, created_at
            ) VALUES (
                %(synthesis_type)s, %(synthesis_number)s, %(executive_summary)s, %(key_insights)s,
                %(questions_for_user)s, %(memory_proposals)s, %(action_recommendations)s,
                %(observations_count)s, %(patterns_count)s, %(created_at)s
            )
            RETURNING id
        """, synthesis)
        return cursor.fetchone()['id']


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
        return cursor.fetchone()['id']
