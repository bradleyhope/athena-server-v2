#!/usr/bin/env python3
"""
Athena Brain 2.0 Schema Migration
Creates the four-layer brain architecture in Neon PostgreSQL.
"""

import os
import psycopg
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://neondb_owner:npg_tk0Re2adLnbM@ep-rough-paper-a4zrxoej-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require')

def run_migration():
    """Execute the Brain 2.0 schema migration."""
    
    conn = psycopg.connect(DATABASE_URL, connect_timeout=30)
    conn.autocommit = True
    cursor = conn.cursor()
    
    logger.info("Starting Brain 2.0 schema migration...")
    
    # Enable UUID extension
    logger.info("Enabling UUID extension...")
    cursor.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")
    
    # =========================================================================
    # LAYER 1: IDENTITY
    # =========================================================================
    logger.info("Creating Identity Layer tables...")
    
    # Core Identity
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS core_identity (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            key TEXT NOT NULL UNIQUE,
            value JSONB NOT NULL,
            description TEXT,
            immutable BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    logger.info("  ✓ core_identity table created")
    
    # Insert core identity values
    identity_values = [
        ('name', '"Athena"', "The AI assistant's name", True),
        ('role', '"Cognitive Extension for Bradley Hope"', 'Primary role and purpose', True),
        ('version', '"2.0"', 'Current system version', False),
        ('timezone', '"Europe/London"', 'Operating timezone', False),
        ('user_email', '"bradley@projectbrazen.com"', 'Primary user email', False),
        ('personality', '{"traits": ["proactive", "thorough", "respectful", "strategic"], "communication_style": "professional but warm", "formality_level": "adaptive"}', 'Personality configuration', False)
    ]
    
    for key, value, desc, immutable in identity_values:
        cursor.execute("""
            INSERT INTO core_identity (key, value, description, immutable)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (key) DO NOTHING
        """, (key, value, desc, immutable))
    logger.info("  ✓ core_identity values inserted")
    
    # Boundaries
    cursor.execute("""
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
        )
    """)
    logger.info("  ✓ boundaries table created")
    
    # Insert default boundaries
    boundaries = [
        ('hard', 'email', 'NEVER send emails autonomously without explicit approval', 'All emails must be drafted and approved', True),
        ('hard', 'financial', 'NEVER make financial transactions or commitments', 'No payments, subscriptions, or financial agreements', True),
        ('hard', 'deletion', 'NEVER delete data without explicit approval', 'All deletions require human confirmation', True),
        ('hard', 'vip_contacts', 'NEVER contact VIP contacts without explicit approval', 'VIP contacts require special handling', True),
        ('soft', 'scheduling', 'Prefer to suggest calendar changes rather than make them', 'Calendar modifications should be proposed', False),
        ('soft', 'notifications', 'Limit notifications to urgent matters only', 'Avoid notification fatigue', False),
        ('contextual', 'autonomy', 'Increase autonomy for routine tasks over time', 'Learn which tasks can be automated', False)
    ]
    
    for btype, cat, rule, desc, req_approval in boundaries:
        cursor.execute("""
            INSERT INTO boundaries (boundary_type, category, rule, description, requires_approval)
            SELECT %s, %s, %s, %s, %s
            WHERE NOT EXISTS (SELECT 1 FROM boundaries WHERE rule = %s)
        """, (btype, cat, rule, desc, req_approval, rule))
    logger.info("  ✓ boundaries values inserted")
    
    # Values
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS values (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            priority INTEGER NOT NULL,
            value_name TEXT NOT NULL UNIQUE,
            description TEXT NOT NULL,
            examples JSONB DEFAULT '[]',
            active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    logger.info("  ✓ values table created")
    
    # Insert core values
    values_data = [
        (1, 'User Sovereignty', "Bradley's decisions and preferences always take precedence", '["Never override explicit user choices", "Ask when uncertain", "Respect stated preferences"]'),
        (2, 'Proactive Assistance', 'Anticipate needs and surface relevant information', '["Flag upcoming deadlines", "Suggest relevant context", "Identify patterns"]'),
        (3, 'Transparency', 'Be clear about reasoning, limitations, and uncertainties', '["Explain why actions are recommended", "Acknowledge when unsure", "Show sources"]'),
        (4, 'Continuous Improvement', 'Learn from interactions and improve over time', '["Track what works", "Adapt to feedback", "Evolve workflows"]'),
        (5, 'Efficiency', 'Minimize friction and maximize value of interactions', '["Batch related items", "Prioritize effectively", "Avoid redundancy"]')
    ]
    
    for priority, name, desc, examples in values_data:
        cursor.execute("""
            INSERT INTO values (priority, value_name, description, examples)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (value_name) DO NOTHING
        """, (priority, name, desc, examples))
    logger.info("  ✓ values data inserted")
    
    # =========================================================================
    # LAYER 2: KNOWLEDGE (workflows - others exist)
    # =========================================================================
    logger.info("Creating Knowledge Layer tables...")
    
    # Workflows
    cursor.execute("""
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
        )
    """)
    logger.info("  ✓ workflows table created")
    
    # Insert default workflows
    workflows = [
        ('morning_brief', 'Generate daily morning brief for Bradley', 'scheduled', 
         '{"cron": "0 6 * * *", "timezone": "Europe/London"}',
         '[{"step": 1, "action": "collect_observations", "params": {"hours": 12}}, {"step": 2, "action": "check_calendar", "params": {"days": 1}}, {"step": 3, "action": "generate_brief", "params": {}}]',
         False),
        ('email_draft_review', 'Draft email responses for review', 'event',
         '{"event": "new_email", "filter": {"requires_response": true}}',
         '[{"step": 1, "action": "analyze_email"}, {"step": 2, "action": "draft_response"}, {"step": 3, "action": "queue_for_approval"}]',
         True),
        ('vip_contact_alert', 'Alert when VIP contact reaches out', 'event',
         '{"event": "new_email", "filter": {"sender_in": "vip_contacts"}}',
         '[{"step": 1, "action": "classify_urgency"}, {"step": 2, "action": "send_alert"}]',
         False),
        ('weekly_synthesis', 'Generate weekly synthesis and evolution proposals', 'scheduled',
         '{"cron": "0 0 * * 0", "timezone": "Europe/London"}',
         '[{"step": 1, "action": "collect_week_data"}, {"step": 2, "action": "run_evolution_engine"}, {"step": 3, "action": "generate_synthesis"}]',
         False)
    ]
    
    for name, desc, ttype, tconfig, steps, req_approval in workflows:
        cursor.execute("""
            INSERT INTO workflows (workflow_name, description, trigger_type, trigger_config, steps, requires_approval)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (workflow_name) DO NOTHING
        """, (name, desc, ttype, tconfig, steps, req_approval))
    logger.info("  ✓ workflows data inserted")
    
    # =========================================================================
    # LAYER 3: STATE
    # =========================================================================
    logger.info("Creating State Layer tables...")
    
    # Context Windows
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS context_windows (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            session_id TEXT NOT NULL,
            context_type TEXT NOT NULL CHECK (context_type IN ('conversation', 'task', 'investigation', 'workflow')),
            context_data JSONB NOT NULL DEFAULT '{}',
            priority INTEGER DEFAULT 0,
            expires_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_context_windows_session ON context_windows(session_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_context_windows_type ON context_windows(context_type)")
    logger.info("  ✓ context_windows table created")
    
    # Pending Actions
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pending_actions (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            action_type TEXT NOT NULL,
            action_data JSONB NOT NULL,
            source_workflow_id UUID,
            source_synthesis_id UUID,
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
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pending_actions_status ON pending_actions(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pending_actions_priority ON pending_actions(priority)")
    logger.info("  ✓ pending_actions table created")
    
    # Session State
    cursor.execute("""
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
        )
    """)
    logger.info("  ✓ session_state table created")
    
    # =========================================================================
    # LAYER 4: EVOLUTION
    # =========================================================================
    logger.info("Creating Evolution Layer tables...")
    
    # Evolution Log
    cursor.execute("""
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
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_evolution_log_type ON evolution_log(evolution_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_evolution_log_status ON evolution_log(status)")
    logger.info("  ✓ evolution_log table created")
    
    # Performance Metrics
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS performance_metrics (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            metric_type TEXT NOT NULL,
            metric_name TEXT NOT NULL,
            metric_value REAL NOT NULL,
            dimensions JSONB DEFAULT '{}',
            period_start TIMESTAMPTZ NOT NULL,
            period_end TIMESTAMPTZ NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_performance_metrics_type ON performance_metrics(metric_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_performance_metrics_period ON performance_metrics(period_start, period_end)")
    logger.info("  ✓ performance_metrics table created")
    
    # Feedback History
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS feedback_history (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            feedback_type TEXT NOT NULL CHECK (feedback_type IN ('approval', 'rejection', 'correction', 'preference', 'explicit')),
            target_type TEXT NOT NULL,
            target_id UUID,
            feedback_data JSONB NOT NULL,
            sentiment TEXT CHECK (sentiment IN ('positive', 'negative', 'neutral')),
            processed BOOLEAN DEFAULT FALSE,
            processed_at TIMESTAMPTZ,
            evolution_id UUID,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedback_history_type ON feedback_history(feedback_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedback_history_processed ON feedback_history(processed)")
    logger.info("  ✓ feedback_history table created")
    
    # =========================================================================
    # BRAIN STATUS & SYNC
    # =========================================================================
    logger.info("Creating Brain Status and Sync tables...")
    
    # Brain Status
    cursor.execute("""
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
        )
    """)
    
    # Insert initial brain status if not exists
    cursor.execute("""
        INSERT INTO brain_status (status, version, config)
        SELECT 'active', '2.0', '{"notion_sync_enabled": true, "evolution_enabled": true, "auto_approve_low_risk": false}'
        WHERE NOT EXISTS (SELECT 1 FROM brain_status)
    """)
    logger.info("  ✓ brain_status table created")
    
    # Notion Sync Log
    cursor.execute("""
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
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_notion_sync_log_source ON notion_sync_log(source_table, source_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_notion_sync_log_status ON notion_sync_log(sync_status)")
    logger.info("  ✓ notion_sync_log table created")
    
    cursor.close()
    conn.close()
    
    logger.info("=" * 60)
    logger.info("Brain 2.0 schema migration completed successfully!")
    logger.info("=" * 60)

if __name__ == "__main__":
    run_migration()
