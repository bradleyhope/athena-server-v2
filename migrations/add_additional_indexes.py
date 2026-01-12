"""
Migration: Add Additional Performance Indexes

This migration adds indexes that were identified during code cleanup
to improve query performance for commonly executed queries.

Run with: python migrations/add_additional_indexes.py
"""

import os
import sys
import logging

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.neon import db_cursor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migration.additional_indexes")


INDEXES_SQL = """
-- Additional performance indexes identified during code cleanup

-- session_state: Frequently queried by session_type and session_date
CREATE INDEX IF NOT EXISTS idx_session_state_type ON session_state(session_type);
CREATE INDEX IF NOT EXISTS idx_session_state_date ON session_state(session_date);

-- synthesis_memory: For filtering impressions and recent synthesis
CREATE INDEX IF NOT EXISTS idx_synthesis_memory_type ON synthesis_memory(synthesis_type);
CREATE INDEX IF NOT EXISTS idx_synthesis_memory_created ON synthesis_memory(created_at);
CREATE INDEX IF NOT EXISTS idx_synthesis_memory_date ON synthesis_memory(synthesis_date);

-- observations: For get_recent_observations() queries
CREATE INDEX IF NOT EXISTS idx_observations_category ON observations(category);
CREATE INDEX IF NOT EXISTS idx_observations_created ON observations(created_at);
CREATE INDEX IF NOT EXISTS idx_observations_source ON observations(source);

-- patterns: For get_recent_patterns() queries
CREATE INDEX IF NOT EXISTS idx_patterns_type ON patterns(pattern_type);
CREATE INDEX IF NOT EXISTS idx_patterns_detected ON patterns(detected_at);
CREATE INDEX IF NOT EXISTS idx_patterns_confidence ON patterns(confidence);

-- context_windows: For cleanup of expired contexts
CREATE INDEX IF NOT EXISTS idx_context_windows_expires ON context_windows(expires_at);
CREATE INDEX IF NOT EXISTS idx_context_windows_priority ON context_windows(priority);

-- entities: Additional useful indexes
CREATE INDEX IF NOT EXISTS idx_entities_confidence ON entities(confidence);
CREATE INDEX IF NOT EXISTS idx_entities_source ON entities(source);
CREATE INDEX IF NOT EXISTS idx_entities_created ON entities(created_at);

-- entity_relationships: Composite index for strength-based queries
CREATE INDEX IF NOT EXISTS idx_entity_rel_strength ON entity_relationships(strength);

-- entity_notes: Valid_until for filtering non-expired notes
CREATE INDEX IF NOT EXISTS idx_entity_notes_valid_until ON entity_notes(valid_until);
CREATE INDEX IF NOT EXISTS idx_entity_notes_created ON entity_notes(created_at);

-- thinking_log: Composite index for session + phase queries
CREATE INDEX IF NOT EXISTS idx_thinking_log_session_phase ON thinking_log(session_id, phase);

-- performance_metrics: Metric name for specific metric lookups
CREATE INDEX IF NOT EXISTS idx_performance_metrics_name ON performance_metrics(metric_name);

-- evolution_log: Confidence for ordering proposals
CREATE INDEX IF NOT EXISTS idx_evolution_log_confidence ON evolution_log(confidence);
CREATE INDEX IF NOT EXISTS idx_evolution_log_category ON evolution_log(category);

-- preferences: Composite for category+key lookups (most common query pattern)
CREATE INDEX IF NOT EXISTS idx_preferences_category_key ON preferences(category, key);

-- core_identity: Key lookups
CREATE INDEX IF NOT EXISTS idx_core_identity_key ON core_identity(key);

-- broadcasts: For session lookups (if table exists)
CREATE INDEX IF NOT EXISTS idx_broadcasts_session ON broadcasts(session_id);
CREATE INDEX IF NOT EXISTS idx_broadcasts_scheduled ON broadcasts(scheduled_for);
CREATE INDEX IF NOT EXISTS idx_broadcasts_status ON broadcasts(status);
"""


def run_migration():
    """Run the migration to add additional indexes."""
    logger.info("Starting migration: add_additional_indexes")

    try:
        with db_cursor() as cursor:
            logger.info("Adding additional performance indexes...")

            # Split by semicolon and execute each statement
            for statement in INDEXES_SQL.strip().split(';'):
                statement = statement.strip()
                if statement and not statement.startswith('--'):
                    try:
                        cursor.execute(statement)
                        # Extract index name for logging
                        if 'CREATE INDEX' in statement:
                            idx_name = statement.split('idx_')[1].split(' ')[0] if 'idx_' in statement else 'unknown'
                            logger.info(f"Created index: idx_{idx_name}")
                    except Exception as e:
                        # Index may already exist or table may not exist
                        logger.warning(f"Statement skipped (may already exist or table missing): {e}")

        logger.info("Migration completed successfully!")
        return True

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False


def verify_indexes():
    """Verify indexes were created and list all custom indexes."""
    logger.info("Verifying indexes...")

    with db_cursor() as cursor:
        cursor.execute("""
            SELECT indexname, tablename
            FROM pg_indexes
            WHERE schemaname = 'public'
            AND indexname LIKE 'idx_%'
            ORDER BY tablename, indexname
        """)
        indexes = cursor.fetchall()

        logger.info(f"Found {len(indexes)} custom indexes:")

        # Group by table
        tables = {}
        for idx in indexes:
            table = idx['tablename']
            if table not in tables:
                tables[table] = []
            tables[table].append(idx['indexname'])

        for table, idx_list in sorted(tables.items()):
            logger.info(f"  {table}:")
            for idx_name in idx_list:
                logger.info(f"    - {idx_name}")

        return indexes


if __name__ == "__main__":
    success = run_migration()
    if success:
        verify_indexes()
    sys.exit(0 if success else 1)
