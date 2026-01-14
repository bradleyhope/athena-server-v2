-- ============================================================================
-- RULE EXPIRATION MIGRATION
-- ============================================================================
-- Adds expires_at column to boundaries, preferences, and canonical_memory tables
-- to allow rules to expire or be deprecated over time.
-- ============================================================================

-- Add expires_at to boundaries table
ALTER TABLE boundaries 
ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ DEFAULT NULL;

-- Add expires_at to preferences table
ALTER TABLE preferences 
ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ DEFAULT NULL;

-- Add expires_at to canonical_memory table
ALTER TABLE canonical_memory 
ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ DEFAULT NULL;

-- Create indexes for efficient expiration queries
CREATE INDEX IF NOT EXISTS idx_boundaries_expires_at ON boundaries(expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_preferences_expires_at ON preferences(expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_canonical_memory_expires_at ON canonical_memory(expires_at) WHERE expires_at IS NOT NULL;

-- Add comment explaining the column
COMMENT ON COLUMN boundaries.expires_at IS 'Optional expiration date for temporary boundaries. NULL means no expiration.';
COMMENT ON COLUMN preferences.expires_at IS 'Optional expiration date for temporary preferences. NULL means no expiration.';
COMMENT ON COLUMN canonical_memory.expires_at IS 'Optional expiration date for temporary facts. NULL means no expiration.';
