"""
Athena Server v2 - Morning Sessions Job
Creates Workspace & Agenda session via Manus API at 5:30 AM London time.

LEAN PROMPT APPROACH:
- Short, action-oriented prompt
- Points to Notion page for detailed instructions
- Athena fetches her own context during the session
"""

import logging
from datetime import datetime
import pytz

from integrations.manus_api import create_manus_task
from db.neon import (
    ensure_active_sessions_table,
    set_active_session,
)
from db.brain import (
    get_brain_status,
    get_pending_actions,
    get_evolution_proposals,
    update_session_state,
)
from config import MANUS_CONNECTORS

logger = logging.getLogger("athena.jobs.morning")

# Reference pages in Notion
WORKSPACE_GUIDE_PAGE_ID = "2e5d44b3-a00b-813f-83fa-f3f3859d3ce8"
COMMAND_CENTER_PAGE_ID = "2e3d44b3-a00b-81ab-bbda-ced57f8c345d"


def get_workspace_agenda_prompt():
    """
    Generate a LEAN Workspace & Agenda session prompt.
    Short and action-oriented - Athena reads her full instructions from Notion.
    """
    london_tz = pytz.timezone('Europe/London')
    now = datetime.now(london_tz)
    
    prompt = f"""You are Athena, Bradley Hope's AI Chief of Staff.

TODAY: {now.strftime('%A, %B %d, %Y')}

## YOUR FIRST ACTION

Read the Workspace & Agenda Session Guide in Notion:
- Use notion-fetch with page ID: {WORKSPACE_GUIDE_PAGE_ID}

This page contains your complete instructions for this session, including:
- Morning checklist (7 steps)
- How to present the daily brief
- How to handle hourly broadcasts
- Recalibration tools
- Key database IDs and API endpoints

## THEN

Follow the checklist in the guide. Present the morning brief to Bradley inline (not as an attachment).

## KEY REFERENCES

- Athena Command Center: {COMMAND_CENTER_PAGE_ID}
- Brain API: https://athena-server-0dce.onrender.com/api/brain
- API Key: athena_api_key_2024 (Bearer token)

Start by reading the Workspace Guide now."""

    return prompt


async def run_morning_sessions():
    """
    Main entry point for the morning sessions cron job.
    Creates the Workspace & Agenda session at 5:30 AM London time.
    """
    logger.info("Starting morning sessions job...")
    
    # Check brain status
    status = get_brain_status()
    if not status or status.get('status') != 'active':
        logger.warning(f"Brain status is not active: {status}")
    
    # Ensure the active_sessions table exists
    try:
        ensure_active_sessions_table()
    except Exception as e:
        logger.warning(f"Could not ensure active_sessions table: {e}")
    
    # Create Workspace & Agenda session
    result = await create_workspace_agenda()
    
    logger.info(f"Morning sessions job complete: {result}")
    return result


async def create_workspace_agenda():
    """
    Create the daily Workspace & Agenda session for Bradley.
    Triggered at 5:30 AM London time.
    Stores the session ID in the database for broadcasts throughout the day.
    """
    logger.info("Creating Workspace & Agenda session...")
    
    # Log pre-session context
    pending_count = len(get_pending_actions())
    evolution_count = len(get_evolution_proposals())
    logger.info(f"Pre-session context: {pending_count} pending actions, {evolution_count} evolution proposals")
    
    try:
        # Generate the lean prompt
        prompt = get_workspace_agenda_prompt()
        
        # Create Manus task with all connectors
        result = await create_manus_task(
            prompt=prompt,
            connectors=MANUS_CONNECTORS
        )
        
        if result and result.get('id'):
            task_id = result.get('id')
            task_url = f"https://manus.im/app/{task_id}"
            
            logger.info(f"Workspace & Agenda session created: {task_id}")
            
            # Store in database for broadcast targeting
            try:
                set_active_session(
                    session_type='workspace_agenda',
                    task_id=task_id,
                    task_url=task_url
                )
                logger.info(f"Stored active session in database: workspace_agenda = {task_id}")
            except Exception as db_error:
                logger.error(f"Failed to store session in database: {db_error}")
            
            # Update session state with creation info
            try:
                update_session_state(
                    session_type='workspace_agenda',
                    handoff_context={
                        'created_at': datetime.utcnow().isoformat(),
                        'task_id': task_id,
                        'pending_actions_at_start': pending_count,
                        'evolution_proposals_at_start': evolution_count
                    }
                )
            except Exception as state_error:
                logger.warning(f"Failed to update session state: {state_error}")
            
            return {
                "status": "success", 
                "task_id": task_id,
                "task_url": task_url,
                "brain_context": {
                    "pending_actions": pending_count,
                    "evolution_proposals": evolution_count
                }
            }
        else:
            logger.error("Failed to create Workspace & Agenda session")
            return {"status": "error", "error": "Failed to create session"}
            
    except Exception as e:
        logger.error(f"Error creating Workspace & Agenda session: {e}")
        return {"status": "error", "error": str(e)}


# Legacy function for backwards compatibility
async def create_agenda_workspace():
    """Alias for create_workspace_agenda."""
    return await create_workspace_agenda()
