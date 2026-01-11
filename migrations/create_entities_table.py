"""
Migration: Create Entities Table

This migration creates:
1. entities table - for storing people, organizations, projects
2. entity_relationships table - for storing relationships between entities

Run with: python migrations/create_entities_table.py
"""

import os
import sys
import logging

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.neon import db_cursor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migration.entities")


ENTITIES_TABLE_SQL = """
-- Core entities table for storing people, organizations, projects
CREATE TABLE IF NOT EXISTS entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type VARCHAR(50) NOT NULL, -- 'person', 'organization', 'project', 'location'
    name VARCHAR(255) NOT NULL,
    description TEXT,
    aliases JSONB DEFAULT '[]'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb, -- Type-specific fields
    access_tier VARCHAR(50) DEFAULT 'default', -- For access control (e.g., 'vip', 'restricted')
    source VARCHAR(200), -- Where this entity was learned from
    confidence DECIMAL(3,2) DEFAULT 1.0, -- Confidence in this entity's accuracy
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for entities
CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name);
CREATE INDEX IF NOT EXISTS idx_entities_access_tier ON entities(access_tier);
CREATE INDEX IF NOT EXISTS idx_entities_active ON entities(active);

-- Full-text search index on name and description
CREATE INDEX IF NOT EXISTS idx_entities_search ON entities USING gin(to_tsvector('english', name || ' ' || COALESCE(description, '')));
"""


RELATIONSHIPS_TABLE_SQL = """
-- Relationships between entities
CREATE TABLE IF NOT EXISTS entity_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_entity_id UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    target_entity_id UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    relationship_type VARCHAR(100) NOT NULL, -- 'employee_of', 'works_on', 'member_of', 'knows', 'manages'
    description TEXT,
    strength DECIMAL(3,2) DEFAULT 1.0, -- Relationship strength/importance
    start_date DATE,
    end_date DATE,
    metadata JSONB DEFAULT '{}'::jsonb,
    source VARCHAR(200), -- Where this relationship was learned from
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(source_entity_id, target_entity_id, relationship_type)
);

-- Indexes for relationships
CREATE INDEX IF NOT EXISTS idx_entity_rel_source ON entity_relationships(source_entity_id);
CREATE INDEX IF NOT EXISTS idx_entity_rel_target ON entity_relationships(target_entity_id);
CREATE INDEX IF NOT EXISTS idx_entity_rel_type ON entity_relationships(relationship_type);
CREATE INDEX IF NOT EXISTS idx_entity_rel_active ON entity_relationships(active);
"""


ENTITY_NOTES_TABLE_SQL = """
-- Notes and interactions related to entities
CREATE TABLE IF NOT EXISTS entity_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    note_type VARCHAR(50) NOT NULL, -- 'interaction', 'preference', 'context', 'reminder'
    content TEXT NOT NULL,
    importance VARCHAR(20) DEFAULT 'normal', -- 'low', 'normal', 'high', 'critical'
    valid_from TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    valid_until TIMESTAMP WITH TIME ZONE, -- NULL means no expiration
    source VARCHAR(200),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for entity notes
CREATE INDEX IF NOT EXISTS idx_entity_notes_entity ON entity_notes(entity_id);
CREATE INDEX IF NOT EXISTS idx_entity_notes_type ON entity_notes(note_type);
CREATE INDEX IF NOT EXISTS idx_entity_notes_importance ON entity_notes(importance);
"""


def run_migration():
    """Run the migration to create entities tables."""
    logger.info("Starting migration: create_entities_table")
    
    try:
        with db_cursor() as cursor:
            # Create entities table
            logger.info("Creating entities table...")
            cursor.execute(ENTITIES_TABLE_SQL)
            logger.info("Entities table created")
            
            # Create relationships table
            logger.info("Creating entity_relationships table...")
            cursor.execute(RELATIONSHIPS_TABLE_SQL)
            logger.info("Entity relationships table created")
            
            # Create notes table
            logger.info("Creating entity_notes table...")
            cursor.execute(ENTITY_NOTES_TABLE_SQL)
            logger.info("Entity notes table created")
            
        logger.info("Migration completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_tables():
    """Verify that tables were created."""
    logger.info("Verifying tables...")
    
    with db_cursor() as cursor:
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('entities', 'entity_relationships', 'entity_notes')
            ORDER BY table_name
        """)
        tables = cursor.fetchall()
        
        logger.info(f"Found {len(tables)} entity-related tables:")
        for table in tables:
            logger.info(f"  - {table['table_name']}")
        
        return len(tables) == 3


if __name__ == "__main__":
    success = run_migration()
    if success:
        verify_tables()
    sys.exit(0 if success else 1)
