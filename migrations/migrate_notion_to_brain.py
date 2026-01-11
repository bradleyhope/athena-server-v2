"""
Athena Brain 2.0 - Notion Data Migration
Migrates existing Notion data into the brain database.
"""

import os
import json
import logging
from datetime import datetime

import psycopg

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migration")

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_connection():
    return psycopg.connect(DATABASE_URL)

def migrate_canonical_memory():
    """Migrate canonical memory entries from Notion."""
    logger.info("Migrating canonical memory...")
    
    # Communication Preferences
    memories = [
        ("communication", "email_sign_off", "Best,", "Standard email sign-off"),
        ("communication", "response_style", "Brief, professional", "Preferred response style"),
        ("communication", "working_hours", "London timezone", "Working timezone"),
        ("scheduling", "admin_task_days", "Tuesdays or Wednesdays before 3pm", "Preferred days for admin tasks"),
        ("scheduling", "admin_task_reason", "School pickup at 3pm makes these days feel shortened, more tolerable for annoying admin work", "Reason for admin day preference"),
        ("scheduling", "admin_avoid_days", "Monday, Thursday, Friday", "Days to avoid for admin tasks"),
        ("projects", "brazen_newsletters", {"priority": "High", "status": "Active"}, "Project Brazen newsletters priority"),
        ("projects", "the_closer", {"schedule": "Daily", "priority": "High"}, "The Closer newsletter schedule"),
        ("projects", "whale_hunting", {"schedule": "Weekly", "priority": "High"}, "Whale Hunting newsletter schedule"),
    ]
    
    with get_connection() as conn:
        with conn.cursor() as cursor:
            for category, key, value, description in memories:
                cursor.execute("""
                    INSERT INTO canonical_memory (category, key, value, description, approved_at, approved_in_session)
                    VALUES (%s, %s, %s, %s, NOW(), 'notion_migration')
                    ON CONFLICT DO NOTHING
                """, (category, key, json.dumps(value), description))
            
            conn.commit()
            logger.info(f"Migrated {len(memories)} canonical memory entries")

def migrate_preferences():
    """Migrate preferences to the preferences table."""
    logger.info("Migrating preferences...")
    
    preferences = [
        ("communication", "email_sign_off", "Best,", 1.0),
        ("communication", "response_style", "Brief, professional", 1.0),
        ("scheduling", "working_timezone", "Europe/London", 1.0),
        ("scheduling", "admin_task_days", "Tuesday, Wednesday", 1.0),
        ("scheduling", "admin_task_time", "Before 3pm", 1.0),
        ("scheduling", "admin_avoid_days", "Monday, Thursday, Friday", 0.9),
        ("newsletter", "the_closer_schedule", "Daily", 1.0),
        ("newsletter", "whale_hunting_schedule", "Weekly", 1.0),
    ]
    
    with get_connection() as conn:
        with conn.cursor() as cursor:
            for category, pref_key, pref_value, confidence in preferences:
                cursor.execute("""
                    INSERT INTO preferences (category, key, value, confidence, source)
                    VALUES (%s, %s, %s, %s, 'notion_migration')
                    ON CONFLICT (category, key) DO UPDATE SET
                        value = EXCLUDED.value,
                        confidence = EXCLUDED.confidence,
                        updated_at = NOW()
                """, (category, pref_key, json.dumps(pref_value), confidence))
            
            conn.commit()
            logger.info(f"Migrated {len(preferences)} preferences")

def migrate_boundaries():
    """Ensure all boundaries from Policies & Rules are in the brain."""
    logger.info("Checking boundaries...")
    
    # These should already exist from the initial migration, but let's verify
    boundaries = [
        # Hard boundaries (FORBIDDEN)
        ("hard", "email", "NEVER send emails autonomously - drafts only", True),
        ("hard", "calendar", "NEVER modify calendar - propose only", True),
        ("hard", "project_creation", "NEVER create projects autonomously - propose only", True),
        ("hard", "data_deletion", "NEVER delete data - append only system", True),
        ("hard", "vip_contacts", "NEVER take action on VIP contacts without explicit approval", True),
        ("hard", "budget", "NEVER exceed $500/month AI API budget", True),
        # Soft boundaries (REQUIRES_APPROVAL)
        ("soft", "notion_edits", "Can edit non-protected Notion pages (Tier 2+)", True),
        ("soft", "task_creation", "Can create tasks autonomously", True),
    ]
    
    with get_connection() as conn:
        with conn.cursor() as cursor:
            for boundary_type, category, rule, active in boundaries:
                cursor.execute("""
                    INSERT INTO boundaries (boundary_type, category, rule, active)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (boundary_type, category, rule, active))
            
            conn.commit()
            logger.info(f"Verified {len(boundaries)} boundaries")

def migrate_vip_categories():
    """Migrate VIP contact categories as entities."""
    logger.info("Migrating VIP categories...")
    
    # VIP categories from Notion
    vip_categories = [
        ("vip_category", "Investor", {"description": "Current or potential investors", "default_action": "Always ask"}),
        ("vip_category", "Client", {"description": "Major clients", "default_action": "Always ask"}),
        ("vip_category", "Partner", {"description": "Business partners", "default_action": "Always ask"}),
        ("vip_category", "Personal", {"description": "Close friends/family", "default_action": "Always ask"}),
        ("vip_category", "Media", {"description": "Journalists, editors", "default_action": "Always ask"}),
    ]
    
    with get_connection() as conn:
        with conn.cursor() as cursor:
            for entity_type, canonical_name, metadata in vip_categories:
                cursor.execute("""
                    INSERT INTO entities (entity_type, canonical_name, metadata)
                    VALUES (%s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (entity_type, canonical_name, json.dumps(metadata)))
            
            conn.commit()
            logger.info(f"Migrated {len(vip_categories)} VIP categories")

def migrate_workflows():
    """Ensure workflows are properly configured."""
    logger.info("Checking workflows...")
    
    workflows = [
        (
            "morning_brief_delivery",
            "Deliver morning brief to Bradley",
            "scheduled",
            {"cron": "0 6 * * *", "timezone": "Europe/London"},
            [
                {"step": 1, "action": "fetch_brain_context", "endpoint": "/api/brain/session-brief/agenda_workspace"},
                {"step": 2, "action": "fetch_calendar", "tool": "google-calendar-list-events"},
                {"step": 3, "action": "check_urgent_email", "tool": "gmail-list-messages", "query": "is:unread"},
                {"step": 4, "action": "check_pending_actions", "endpoint": "/api/brain/actions/pending"},
                {"step": 5, "action": "format_brief", "template": "daily_brief_v2"},
                {"step": 6, "action": "present_to_bradley", "format": "inline_text"}
            ],
            False
        ),
        (
            "email_draft_review",
            "Draft emails for Bradley to review",
            "event",
            {"event_type": "email_draft_requested"},
            [
                {"step": 1, "action": "check_vip_status", "endpoint": "/api/brain/boundaries/check"},
                {"step": 2, "action": "load_preferences", "endpoint": "/api/brain/preferences"},
                {"step": 3, "action": "draft_email", "use_sign_off": "Best,"},
                {"step": 4, "action": "store_draft", "table": "email_drafts"},
                {"step": 5, "action": "present_for_approval"}
            ],
            True
        ),
        (
            "vip_contact_alert",
            "Alert when VIP contact communication detected",
            "event",
            {"event_type": "vip_email_received"},
            [
                {"step": 1, "action": "identify_vip", "endpoint": "/api/brain/entities?type=vip_contact"},
                {"step": 2, "action": "flag_priority", "level": "high"},
                {"step": 3, "action": "queue_for_morning_brief"},
                {"step": 4, "action": "do_not_auto_respond"}
            ],
            False
        ),
        (
            "weekly_synthesis",
            "Weekly synthesis and evolution proposal",
            "scheduled",
            {"cron": "0 0 * * 0", "timezone": "Europe/London"},
            [
                {"step": 1, "action": "gather_week_observations"},
                {"step": 2, "action": "run_pattern_detection"},
                {"step": 3, "action": "generate_synthesis", "model": "tier3"},
                {"step": 4, "action": "propose_evolutions"},
                {"step": 5, "action": "update_brain_status"}
            ],
            False
        ),
    ]
    
    with get_connection() as conn:
        with conn.cursor() as cursor:
            for name, description, trigger_type, trigger_config, steps, requires_approval in workflows:
                cursor.execute("""
                    INSERT INTO workflows (workflow_name, description, trigger_type, trigger_config, steps, requires_approval, enabled)
                    VALUES (%s, %s, %s, %s, %s, %s, true)
                    ON CONFLICT (workflow_name) DO UPDATE SET
                        description = EXCLUDED.description,
                        trigger_type = EXCLUDED.trigger_type,
                        trigger_config = EXCLUDED.trigger_config,
                        steps = EXCLUDED.steps,
                        requires_approval = EXCLUDED.requires_approval,
                        updated_at = NOW()
                """, (name, description, trigger_type, json.dumps(trigger_config), json.dumps(steps), requires_approval))
            
            conn.commit()
            logger.info(f"Configured {len(workflows)} workflows")

def verify_migration():
    """Verify the migration was successful."""
    logger.info("Verifying migration...")
    
    with get_connection() as conn:
        with conn.cursor() as cursor:
            # Count records in each table
            tables = ['canonical_memory', 'preferences', 'boundaries', 'entities', 'workflows']
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                logger.info(f"  {table}: {count} records")

def run_migration():
    """Run all migrations."""
    logger.info("=" * 60)
    logger.info("Starting Notion to Brain migration...")
    logger.info("=" * 60)
    
    migrate_canonical_memory()
    migrate_preferences()
    migrate_boundaries()
    migrate_vip_categories()
    migrate_workflows()
    
    logger.info("-" * 60)
    verify_migration()
    
    logger.info("=" * 60)
    logger.info("Migration complete!")
    logger.info("=" * 60)

if __name__ == "__main__":
    run_migration()
