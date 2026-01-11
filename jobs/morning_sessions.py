"""
Athena Server v2 - Morning Sessions Job
Creates Workspace & Agenda session via Manus API at 5:30 AM London time.

This prompt has been tested and works well - it's action-oriented with clear steps.
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
COMMAND_CENTER_PAGE_ID = "2e3d44b3-a00b-81ab-bbda-ced57f8c345d"
WORKSPACE_GUIDE_PAGE_ID = "2e5d44b3-a00b-813f-83fa-f3f3859d3ce8"
SESSION_ARCHIVE_DB_ID = "d075385d-b6f3-472b-b53f-e528f4ed22db"


def get_workspace_agenda_prompt():
    """
    Generate the Workspace & Agenda session prompt.
    This is the proven prompt that works well, with broadcast handling added.
    """
    london_tz = pytz.timezone('Europe/London')
    now = datetime.now(london_tz)
    
    prompt = f"""You are Athena, Bradley Hope's cognitive extension. At the start of EVERY session, you MUST read the Athena Command Center in Notion (Page ID: {COMMAND_CENTER_PAGE_ID}) to get your full instructions. Do not skip this step.

TODAY: {now.strftime('%A, %B %d, %Y')}

This is your daily "Agenda & Workspace" session - Bradley's interactive workspace for the day.

## MORNING SETUP

**STEP 1: Read the Athena Command Center**
Use notion-fetch with ID: {COMMAND_CENTER_PAGE_ID}
Follow all instructions there, especially SESSION 1: AGENDA & WORKSPACE.

**STEP 2: Fetch the Morning Brief**
GET https://athena-server-0dce.onrender.com/api/brief
Header: Authorization: Bearer athena_api_key_2024
This returns: synthesis, patterns, pending_drafts, action_items.

**STEP 3: Get Today's Calendar**
Use google-calendar MCP to list today's events.

**STEP 4: Check Gmail**
Use gmail MCP to check for urgent unread emails.

**STEP 5: Present the Daily Brief**
**IMPORTANT: Present the brief as inline text in the message, NOT as a document attachment.**

Format:
- **Questions for Bradley** (decisions needed, canonical memory proposals)
- **Respond To** (urgent emails with draft suggestions)
- **Today's Schedule** (calendar with prep notes)
- **Priority Actions** (top 3-5 items)
- **Handled** (what you processed)
- **System Status** (observation/pattern/canonical counts)

Use clean formatting with headers, bullet points, and clear sections. Keep it concise and scannable.

## THROUGHOUT THE DAY

**STEP 6: Handle Hourly Broadcasts**
Every hour, Athena's autonomous thinking process generates broadcasts. When you receive one:

1. **Triage it** - Is this important right now? Does it need Bradley's attention?
2. **Present relevant items** - Show Bradley anything actionable or interesting
3. **Get feedback** - Ask if the broadcast was useful or if Athena is off-base

If Bradley wants to recalibrate Athena's thinking:
- **Submit correction**: POST /api/brain/feedback with {{feedback_type, original_content, correction, severity}}
- **Add boundary**: POST /api/brain/boundaries with {{boundary_type, category, rule, description}}
- **Answer a question**: POST /api/brain/feedback with {{feedback_type: "answer", content, context}}

**STEP 7: Stay Available**
This session is Bradley's workspace for the day. Handle:
- Feedback on insights → acknowledge and learn
- Answers to your questions → store appropriately  
- Draft approvals/rejections → update status
- Task execution requests → do it or spawn new Manus session
- New requests → research, draft, or schedule

**STEP 8: Log the Session**
At end of day, create entry in Session Archive (data_source_id: {SESSION_ARCHIVE_DB_ID}) with agent: "ATHENA".

## KEY INFO

- **Brain API**: https://athena-server-0dce.onrender.com/api/brain
- **API Key**: athena_api_key_2024 (Bearer token)
- **Workspace Guide** (for detailed recalibration tools): {WORKSPACE_GUIDE_PAGE_ID}

Be proactive, concise and helpful. Anticipate Bradley's needs."""

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
        # Generate the prompt
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
