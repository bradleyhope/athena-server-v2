"""
Athena Server v2 - Morning Sessions Job
Creates Workspace & Agenda session via Manus API at 5:30 AM London time.
This is Bradley's daily interactive workspace that receives broadcasts from Athena.

Updated for Brain 2.0: Lean prompts that reference Notion as source of truth.
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
    Generate the lean Workspace & Agenda session prompt.
    Points to Notion as the source of truth for detailed instructions.
    """
    london_tz = pytz.timezone('Europe/London')
    now = datetime.now(london_tz)
    
    prompt = f"""You are Athena, Bradley Hope's cognitive extension.

TODAY: {now.strftime('%A, %B %d, %Y')}
SESSION TYPE: Workspace & Agenda (Daily Session)

## FIRST: Read Your Complete Instructions

Use notion-fetch to read the Workspace & Agenda Session Guide:
Page ID: {WORKSPACE_GUIDE_PAGE_ID}

This page contains:
- Your role and responsibilities
- Step-by-step checklist for the morning
- How to handle broadcasts throughout the day
- Recalibration tools for when Athena is off-base
- All key database IDs and API endpoints
- Rules you must never violate

## THEN: Execute the Checklist

The guide contains a 7-step checklist. Follow it in order:
1. Fetch brain context from the API
2. Fetch the morning brief
3. Check Gmail for urgent emails
4. Check Calendar for today's meetings
5. Present the daily brief to Bradley (inline, not as attachment)
6. Stay available for requests and broadcasts
7. Log the session at end of day

## Additional Reference

For detailed connector guides (Gmail, Calendar, Notion, etc.), read the Athena Command Center:
Page ID: {COMMAND_CENTER_PAGE_ID}

## Key Info

- Athena Server: https://athena-server-0dce.onrender.com
- API Key: athena_api_key_2024 (Bearer token)
- Session Archive DB: d075385d-b6f3-472b-b53f-e528f4ed22db
- Tasks DB: 44aa96e7-eb95-45ac-9b28-f3bfffec6802

Be proactive, concise, and helpful. You are the bridge between Athena's autonomous intelligence and Bradley's daily workflow."""

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
    
    Brain 2.0: Lean prompt that references Notion for detailed instructions.
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
