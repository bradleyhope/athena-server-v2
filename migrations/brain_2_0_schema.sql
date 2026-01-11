-- ============================================================================
-- ATHENA BRAIN 2.0 SCHEMA MIGRATION
-- ============================================================================
-- This migration creates the four-layer brain architecture:
-- 1. Identity Layer: core_identity, boundaries, values
-- 2. Knowledge Layer: workflows (new), canonical_memory (exists), preferences (exists), entities (exists)
-- 3. State Layer: context_windows, pending_actions, session_state
-- 4. Evolution Layer: evolution_log, performance_metrics, feedback_history
-- ============================================================================

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- LAYER 1: IDENTITY
-- ============================================================================

-- Core Identity: Athena's fundamental identity and purpose
CREATE TABLE IF NOT EXISTS core_identity (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key TEXT NOT NULL UNIQUE,
    value JSONB NOT NULL,
    description TEXT,
    immutable BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert core identity if not exists
INSERT INTO core_identity (key, value, description, immutable) VALUES
    ('name', '"Athena"', 'The AI assistant''s name', TRUE),
    ('role', '"Cognitive Extension for Bradley Hope"', 'Primary role and purpose', TRUE),
    ('version', '"2.0"', 'Current system version', FALSE),
    ('timezone', '"Europe/London"', 'Operating timezone', FALSE),
    ('user_email', '"bradley@projectbrazen.com"', 'Primary user email', FALSE),
    ('personality', '{"traits": ["proactive", "thorough", "respectful", "strategic"], "communication_style": "professional but warm", "formality_level": "adaptive"}', 'Personality configuration', FALSE)
ON CONFLICT (key) DO NOTHING;

-- Boundaries: What Athena can and cannot do
CREATE TABLE IF NOT EXISTS boundaries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    boundary_type TEXT NOT NULL CHECK (boundary_type IN ('hard', 'soft', 'contextual')),
    category TEXT NOT NULL,
    rule TEXT NOT NULL,
    description TEXT,
    exceptions JSONB DEFAULT '[]',
    requires_approval BOOLEAN DEFAULT FALSE,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert default boundaries
INSERT INTO boundaries (boundary_type, category, rule, description, requires_approval) VALUES
    ('hard', 'email', 'NEVER send emails autonomously without explicit approval', 'All emails must be drafted and approved', TRUE),
    ('hard', 'financial', 'NEVER make financial transactions or commitments', 'No payments, subscriptions, or financial agreements', TRUE),
    ('hard', 'deletion', 'NEVER delete data without explicit approval', 'All deletions require human confirmation', TRUE),
    ('hard', 'vip_contacts', 'NEVER contact VIP contacts without explicit approval', 'VIP contacts require special handling', TRUE),
    ('soft', 'scheduling', 'Prefer to suggest calendar changes rather than make them', 'Calendar modifications should be proposed', FALSE),
    ('soft', 'notifications', 'Limit notifications to urgent matters only', 'Avoid notification fatigue', FALSE),
    ('contextual', 'autonomy', 'Increase autonomy for routine tasks over time', 'Learn which tasks can be automated', FALSE)
ON CONFLICT DO NOTHING;

-- Values: Athena's operating principles
CREATE TABLE IF NOT EXISTS values (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    priority INTEGER NOT NULL,
    value_name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL,
    examples JSONB DEFAULT '[]',
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert core values
INSERT INTO values (priority, value_name, description, examples) VALUES
    (1, 'User Sovereignty', 'Bradley''s decisions and preferences always take precedence', '["Never override explicit user choices", "Ask when uncertain", "Respect stated preferences"]'),
    (2, 'Proactive Assistance', 'Anticipate needs and surface relevant information', '["Flag upcoming deadlines", "Suggest relevant context", "Identify patterns"]'),
    (3, 'Transparency', 'Be clear about reasoning, limitations, and uncertainties', '["Explain why actions are recommended", "Acknowledge when unsure", "Show sources"]'),
    (4, 'Continuous Improvement', 'Learn from interactions and improve over time', '["Track what works", "Adapt to feedback", "Evolve workflows"]'),
    (5, 'Efficiency', 'Minimize friction and maximize value of interactions', '["Batch related items", "Prioritize effectively", "Avoid redundancy"]')
ON CONFLICT (value_name) DO NOTHING;

-- ============================================================================
-- LAYER 2: KNOWLEDGE (workflows table - others exist)
-- ============================================================================

-- Workflows: Learned and defined operational procedures
CREATE TABLE IF NOT EXISTS workflows (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workflow_name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL,
    trigger_type TEXT NOT NULL CHECK (trigger_type IN ('manual', 'scheduled', 'event', 'condition')),
    trigger_config JSONB DEFAULT '{}',
    steps JSONB NOT NULL DEFAULT '[]',
    input_schema JSONB DEFAULT '{}',
    output_schema JSONB DEFAULT '{}',
    requires_approval BOOLEAN DEFAULT FALSE,
    approval_threshold TEXT DEFAULT 'always' CHECK (approval_threshold IN ('always', 'high_impact', 'never')),
    enabled BOOLEAN DEFAULT TRUE,
    execution_count INTEGER DEFAULT 0,
    last_executed_at TIMESTAMPTZ,
    success_rate REAL DEFAULT 0.0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert default workflows
INSERT INTO workflows (workflow_name, description, trigger_type, trigger_config, steps, requires_approval) VALUES
    ('morning_brief', 'Generate daily morning brief for Bradley', 'scheduled', '{"cron": "0 6 * * *", "timezone": "Europe/London"}', 
     '[{"step": 1, "action": "collect_observations", "params": {"hours": 12}}, {"step": 2, "action": "check_calendar", "params": {"days": 1}}, {"step": 3, "action": "generate_brief", "params": {}}]', FALSE),
    ('email_draft_review', 'Draft email responses for review', 'event', '{"event": "new_email", "filter": {"requires_response": true}}',
     '[{"step": 1, "action": "analyze_email"}, {"step": 2, "action": "draft_response"}, {"step": 3, "action": "queue_for_approval"}]', TRUE),
    ('vip_contact_alert', 'Alert when VIP contact reaches out', 'event', '{"event": "new_email", "filter": {"sender_in": "vip_contacts"}}',
     '[{"step": 1, "action": "classify_urgency"}, {"step": 2, "action": "send_alert"}]', FALSE),
    ('weekly_synthesis', 'Generate weekly synthesis and evolution proposals', 'scheduled', '{"cron": "0 0 * * 0", "timezone": "Europe/London"}',
     '[{"step": 1, "action": "collect_week_data"}, {"step": 2, "action": "run_evolution_engine"}, {"step": 3, "action": "generate_synthesis"}]', FALSE)
ON CONFLICT (workflow_name) DO NOTHING;

-- ============================================================================
-- LAYER 3: STATE
-- ============================================================================

-- Context Windows: Active context for ongoing interactions
CREATE TABLE IF NOT EXISTS context_windows (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id TEXT NOT NULL,
    context_type TEXT NOT NULL CHECK (context_type IN ('conversation', 'task', 'investigation', 'workflow')),
    context_data JSONB NOT NULL DEFAULT '{}',
    priority INTEGER DEFAULT 0,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for efficient context retrieval
CREATE INDEX IF NOT EXISTS idx_context_windows_session ON context_windows(session_id);
CREATE INDEX IF NOT EXISTS idx_context_windows_type ON context_windows(context_type);

-- Pending Actions: Actions awaiting approval or execution
CREATE TABLE IF NOT EXISTS pending_actions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    action_type TEXT NOT NULL,
    action_data JSONB NOT NULL,
    source_workflow_id UUID REFERENCES workflows(id),
    source_synthesis_id UUID REFERENCES synthesis_memory(id),
    priority TEXT DEFAULT 'normal' CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'executed', 'expired')),
    requires_approval BOOLEAN DEFAULT TRUE,
    approval_reason TEXT,
    approved_by TEXT,
    approved_at TIMESTAMPTZ,
    executed_at TIMESTAMPTZ,
    result JSONB,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for pending actions
CREATE INDEX IF NOT EXISTS idx_pending_actions_status ON pending_actions(status);
CREATE INDEX IF NOT EXISTS idx_pending_actions_priority ON pending_actions(priority);

-- Session State: Persistent state across Manus sessions
CREATE TABLE IF NOT EXISTS session_state (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_type TEXT NOT NULL CHECK (session_type IN ('athena_thinking', 'agenda_workspace', 'architecture', 'investigation', 'other')),
    session_date DATE NOT NULL,
    manus_task_id TEXT,
    manus_task_url TEXT,
    state_data JSONB DEFAULT '{}',
    handoff_context JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(session_type, session_date)
);

-- ============================================================================
-- LAYER 4: EVOLUTION
-- ============================================================================

-- Evolution Log: Record of all system changes and improvements
CREATE TABLE IF NOT EXISTS evolution_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    evolution_type TEXT NOT NULL CHECK (evolution_type IN ('workflow_update', 'preference_learned', 'boundary_adjusted', 'memory_added', 'pattern_codified', 'performance_improvement')),
    category TEXT NOT NULL,
    description TEXT NOT NULL,
    change_data JSONB NOT NULL,
    source TEXT NOT NULL CHECK (source IN ('synthesis', 'feedback', 'observation', 'manual', 'evolution_engine')),
    source_id UUID,
    confidence REAL DEFAULT 0.5 CHECK (confidence >= 0 AND confidence <= 1),
    status TEXT DEFAULT 'proposed' CHECK (status IN ('proposed', 'approved', 'rejected', 'applied', 'reverted')),
    approved_by TEXT,
    approved_at TIMESTAMPTZ,
    applied_at TIMESTAMPTZ,
    impact_assessment JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for evolution log
CREATE INDEX IF NOT EXISTS idx_evolution_log_type ON evolution_log(evolution_type);
CREATE INDEX IF NOT EXISTS idx_evolution_log_status ON evolution_log(status);

-- Performance Metrics: Track system performance over time
CREATE TABLE IF NOT EXISTS performance_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_type TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value REAL NOT NULL,
    dimensions JSONB DEFAULT '{}',
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for metrics
CREATE INDEX IF NOT EXISTS idx_performance_metrics_type ON performance_metrics(metric_type);
CREATE INDEX IF NOT EXISTS idx_performance_metrics_period ON performance_metrics(period_start, period_end);

-- Feedback History: Record of user feedback for learning
CREATE TABLE IF NOT EXISTS feedback_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    feedback_type TEXT NOT NULL CHECK (feedback_type IN ('approval', 'rejection', 'correction', 'preference', 'explicit')),
    target_type TEXT NOT NULL,
    target_id UUID,
    feedback_data JSONB NOT NULL,
    sentiment TEXT CHECK (sentiment IN ('positive', 'negative', 'neutral')),
    processed BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMPTZ,
    evolution_id UUID REFERENCES evolution_log(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for feedback
CREATE INDEX IF NOT EXISTS idx_feedback_history_type ON feedback_history(feedback_type);
CREATE INDEX IF NOT EXISTS idx_feedback_history_processed ON feedback_history(processed);

-- ============================================================================
-- BRAIN STATUS TABLE
-- ============================================================================

-- Brain Status: Overall system status and configuration
CREATE TABLE IF NOT EXISTS brain_status (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'paused', 'maintenance', 'emergency_stop')),
    version TEXT NOT NULL DEFAULT '2.0',
    last_synthesis_at TIMESTAMPTZ,
    last_evolution_at TIMESTAMPTZ,
    last_notion_sync_at TIMESTAMPTZ,
    config JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert initial brain status
INSERT INTO brain_status (status, version, config) VALUES
    ('active', '2.0', '{"notion_sync_enabled": true, "evolution_enabled": true, "auto_approve_low_risk": false}')
ON CONFLICT DO NOTHING;

-- ============================================================================
-- NOTION SYNC TRACKING
-- ============================================================================

-- Notion Sync Log: Track what has been synced to Notion
CREATE TABLE IF NOT EXISTS notion_sync_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_table TEXT NOT NULL,
    source_id UUID NOT NULL,
    notion_page_id TEXT,
    notion_database_id TEXT,
    sync_type TEXT NOT NULL CHECK (sync_type IN ('create', 'update', 'delete')),
    sync_status TEXT DEFAULT 'pending' CHECK (sync_status IN ('pending', 'success', 'failed')),
    error_message TEXT,
    synced_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for sync log
CREATE INDEX IF NOT EXISTS idx_notion_sync_log_source ON notion_sync_log(source_table, source_id);
CREATE INDEX IF NOT EXISTS idx_notion_sync_log_status ON notion_sync_log(sync_status);

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to all tables with updated_at
DO $$
DECLARE
    t TEXT;
BEGIN
    FOR t IN 
        SELECT table_name 
        FROM information_schema.columns 
        WHERE column_name = 'updated_at' 
        AND table_schema = 'public'
    LOOP
        EXECUTE format('
            DROP TRIGGER IF EXISTS update_%I_updated_at ON %I;
            CREATE TRIGGER update_%I_updated_at
            BEFORE UPDATE ON %I
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
        ', t, t, t, t);
    END LOOP;
END;
$$;

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================
