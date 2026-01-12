"""
Migration: Add Broadcast Idempotency

This migration adds:
1. Unique constraint on broadcasts.session_id to prevent duplicates
2. Updates store_broadcast to use ON CONFLICT for idempotency

Run with: python migrations/add_broadcast_idempotency.py
"""

import os
import sys
import logging

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.neon import db_cursor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migration.broadcast_idempotency")


def run_migration():
    """Run the migration to add broadcast idempotency."""
    logger.info("Starting migration: add_broadcast_idempotency")

    try:
        with db_cursor() as cursor:
            # First, check if the constraint already exists
            cursor.execute("""
                SELECT 1 FROM information_schema.table_constraints
                WHERE constraint_name = 'unique_broadcast_session'
                AND table_name = 'broadcasts'
            """)
            if cursor.fetchone():
                logger.info("Constraint unique_broadcast_session already exists")
                return True

            # Check for duplicate session_ids before adding constraint
            cursor.execute("""
                SELECT session_id, COUNT(*) as count
                FROM broadcasts
                GROUP BY session_id
                HAVING COUNT(*) > 1
            """)
            duplicates = cursor.fetchall()

            if duplicates:
                logger.warning(f"Found {len(duplicates)} duplicate session_ids")
                # Keep only the most recent of each duplicate
                for dup in duplicates:
                    session_id = dup['session_id']
                    logger.info(f"Cleaning up duplicates for session_id: {session_id}")
                    cursor.execute("""
                        DELETE FROM broadcasts
                        WHERE session_id = %s
                        AND id NOT IN (
                            SELECT id FROM broadcasts
                            WHERE session_id = %s
                            ORDER BY created_at DESC
                            LIMIT 1
                        )
                    """, (session_id, session_id))
                    logger.info(f"Removed {cursor.rowcount} duplicate(s)")

            # Now add the unique constraint
            logger.info("Adding unique constraint on broadcasts.session_id")
            cursor.execute("""
                ALTER TABLE broadcasts
                ADD CONSTRAINT unique_broadcast_session UNIQUE (session_id)
            """)
            logger.info("Unique constraint added successfully")

        logger.info("Migration completed successfully!")
        return True

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_constraint():
    """Verify the constraint was created."""
    logger.info("Verifying constraint...")

    with db_cursor() as cursor:
        cursor.execute("""
            SELECT constraint_name, constraint_type
            FROM information_schema.table_constraints
            WHERE table_name = 'broadcasts'
            AND constraint_type = 'UNIQUE'
        """)
        constraints = cursor.fetchall()

        if constraints:
            logger.info("Found unique constraints:")
            for c in constraints:
                logger.info(f"  - {c['constraint_name']}: {c['constraint_type']}")
            return True
        else:
            logger.warning("No unique constraints found on broadcasts table")
            return False


if __name__ == "__main__":
    success = run_migration()
    if success:
        verify_constraint()
    sys.exit(0 if success else 1)
