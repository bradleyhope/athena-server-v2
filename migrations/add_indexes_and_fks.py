"""
Migration: Add Database Indexes and Foreign Keys

This migration adds:
1. Performance indexes on frequently queried columns
2. Foreign key constraints for data integrity

Run with: python migrations/add_indexes_and_fks.py
"""

import os
import sys
import logging

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.neon import db_cursor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migration.indexes")


INDEXES_SQL = """
-- Performance indexes for frequently queried columns

-- thinking_log indexes
CREATE INDEX IF NOT EXISTS idx_thinking_log_session ON thinking_log(session_id);
CREATE INDEX IF NOT EXISTS idx_thinking_log_created ON thinking_log(created_at);
CREATE INDEX IF NOT EXISTS idx_thinking_log_type ON thinking_log(thought_type);

-- canonical_memory indexes
CREATE INDEX IF NOT EXISTS idx_canonical_memory_category ON canonical_memory(category);
CREATE INDEX IF NOT EXISTS idx_canonical_memory_key ON canonical_memory(key);

-- feedback_history indexes
CREATE INDEX IF NOT EXISTS idx_feedback_history_processed ON feedback_history(processed);
CREATE INDEX IF NOT EXISTS idx_feedback_history_created ON feedback_history(created_at);
CREATE INDEX IF NOT EXISTS idx_feedback_history_type ON feedback_history(feedback_type);

-- pending_actions indexes
CREATE INDEX IF NOT EXISTS idx_pending_actions_status ON pending_actions(status);
CREATE INDEX IF NOT EXISTS idx_pending_actions_priority ON pending_actions(priority);
CREATE INDEX IF NOT EXISTS idx_pending_actions_created ON pending_actions(created_at);

-- evolution_log indexes
CREATE INDEX IF NOT EXISTS idx_evolution_log_status ON evolution_log(status);
CREATE INDEX IF NOT EXISTS idx_evolution_log_type ON evolution_log(evolution_type);
CREATE INDEX IF NOT EXISTS idx_evolution_log_created ON evolution_log(created_at);

-- workflows indexes
CREATE INDEX IF NOT EXISTS idx_workflows_enabled ON workflows(enabled);
CREATE INDEX IF NOT EXISTS idx_workflows_trigger ON workflows(trigger_type);

-- preferences indexes
CREATE INDEX IF NOT EXISTS idx_preferences_category ON preferences(category);
CREATE INDEX IF NOT EXISTS idx_preferences_key ON preferences(key);

-- boundaries indexes
CREATE INDEX IF NOT EXISTS idx_boundaries_type ON boundaries(boundary_type);
CREATE INDEX IF NOT EXISTS idx_boundaries_category ON boundaries(category);
CREATE INDEX IF NOT EXISTS idx_boundaries_active ON boundaries(active);

-- values indexes
CREATE INDEX IF NOT EXISTS idx_values_priority ON values(priority);
CREATE INDEX IF NOT EXISTS idx_values_active ON values(active);

-- active_sessions indexes
CREATE INDEX IF NOT EXISTS idx_active_sessions_type ON active_sessions(session_type);
CREATE INDEX IF NOT EXISTS idx_active_sessions_date ON active_sessions(session_date);
"""


FOREIGN_KEYS_SQL = """
-- Foreign key constraints for data integrity
-- Note: Using DO blocks to handle cases where constraints already exist

DO $$ 
BEGIN
    -- pending_actions -> workflows
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'fk_pending_actions_workflow'
    ) THEN
        ALTER TABLE pending_actions 
        ADD CONSTRAINT fk_pending_actions_workflow 
        FOREIGN KEY (source_workflow_id) REFERENCES workflows(id) ON DELETE SET NULL;
    END IF;
END $$;

DO $$ 
BEGIN
    -- feedback_history -> evolution_log
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'fk_feedback_evolution'
    ) THEN
        ALTER TABLE feedback_history 
        ADD CONSTRAINT fk_feedback_evolution 
        FOREIGN KEY (evolution_id) REFERENCES evolution_log(id) ON DELETE SET NULL;
    END IF;
END $$;
"""


def run_migration():
    """Run the migration to add indexes and foreign keys."""
    logger.info("Starting migration: add_indexes_and_fks")
    
    try:
        with db_cursor() as cursor:
            # Add indexes
            logger.info("Adding performance indexes...")
            for statement in INDEXES_SQL.strip().split(';'):
                statement = statement.strip()
                if statement and not statement.startswith('--'):
                    try:
                        cursor.execute(statement)
                        logger.info(f"Executed: {statement[:60]}...")
                    except Exception as e:
                        logger.warning(f"Index statement failed (may already exist): {e}")
            
            # Add foreign keys
            logger.info("Adding foreign key constraints...")
            cursor.execute(FOREIGN_KEYS_SQL)
            logger.info("Foreign key constraints added")
            
        logger.info("Migration completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False


def verify_indexes():
    """Verify that indexes were created."""
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
        for idx in indexes:
            logger.info(f"  - {idx['tablename']}.{idx['indexname']}")
        
        return indexes


if __name__ == "__main__":
    success = run_migration()
    if success:
        verify_indexes()
    sys.exit(0 if success else 1)
