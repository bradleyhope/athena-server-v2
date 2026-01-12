"""
Morning Sessions Job

Spawns the daily Workspace & Agenda session for Bradley Hope.
This is the interactive workspace session that runs throughout the day.
Includes automatic learning loop integration.
"""

import logging
import pytz
from datetime import datetime
from typing import Dict, Any, Optional

from integrations.manus_api import create_manus_task, rename_manus_task
from db.neon import set_active_session
from db.brain import (
    get_core_identity,
    get_boundaries,
    get_pending_actions
)
from config import settings, MANUS_CONNECTORS

logger = logging.getLogger("athena.jobs.morning")


def get_workspace_agenda_prompt():
    """
    Generate the Workspace & Agenda session prompt.
    Task-focused approach that doesn't trigger identity rejection.
    Includes active rules from the learning system.
    """
    london_tz = pytz.timezone('Europe/London')
    now = datetime.now(london_tz)
    
    prompt = f"""# Daily Workspace & Agenda Session for Bradley Hope

**Date**: {now.strftime('%A, %B %d, %Y')}
**Time**: {now.strftime('%H:%M')} London

This task is to prepare and present Bradley Hope's daily brief, then remain available as an interactive workspace throughout the day.

## SETUP STEPS

### Step 1: Read the Athena Command Center
Fetch the Notion page with ID: `{settings.ATHENA_COMMAND_CENTER_ID}`
This contains the full operating instructions and context for this session.

### Step 2: Fetch Active Rules (IMPORTANT)
```
GET https://athena-server-0dce.onrender.com/api/v1/learning/active-rules
Header: Authorization: Bearer athena_api_key_2024
```
This returns boundaries, preferences, and canonical memory that MUST be applied to all actions.

**Key rules to always follow:**
- NEVER create tasks from notifications (OCBC, security alerts, Ghost signups, Scout reports)
- Filter spam aggressively (PR pitches, podcast guesting, event invites → Done/Low Priority)
- ALWAYS reply in-thread (never start new email threads for follow-ups)
- Use "Dear [Name]" for formal emails, not "Hey"
- Schedule admin tasks for Tuesdays/Wednesdays before 3 PM

### Step 3: Query the Athena Tasks Database
Query the Notion database with data_source_id: `{settings.ATHENA_TASKS_DB_ID}`
Look for:
- Tasks completed recently (especially today) - celebrate these wins!
- Tasks due today or overdue
- High priority items that need attention

### Step 4: Fetch the Brain API Brief
```
GET https://athena-server-0dce.onrender.com/api/brief
Header: Authorization: Bearer athena_api_key_2024
```
This returns synthesis, patterns, pending drafts, and action items.

### Step 5: Check Today's Calendar
Use google-calendar MCP to list today's events and meetings.

### Step 6: Check Gmail
Use gmail MCP to check for urgent unread emails that need attention.

### Step 7: Present the Daily Brief
**Present as inline text, NOT as a document attachment.**

Format the brief with these sections:
- **Tasks Completed** - What's been accomplished (from Athena Tasks)
- **Questions for Bradley** - Decisions needed, proposals to review
- **Respond To** - Urgent emails with draft suggestions
- **Today's Schedule** - Calendar events with prep notes
- **Priority Actions** - Top 3-5 items from Athena Tasks
- **System Status** - Brief stats on observations/patterns

Keep it concise and scannable.

## THROUGHOUT THE DAY

This session stays open as Bradley's interactive workspace. Handle:

1. **Task Updates** - When Bradley completes tasks, update them in Athena Tasks database with completion notes
2. **Email Drafts** - Draft responses to emails, get approval before sending
3. **Research Requests** - Research topics and present findings
4. **Scheduling** - Help schedule meetings and manage calendar
5. **New Tasks** - Add new tasks to Athena Tasks database

### Logging Completed Tasks
When a task is marked complete, record:
- Completion timestamp
- Brief notes on how it was solved or outcome
- If it was a bad task (shouldn't have been created), note why for future learning

### Learning from the Session
When you discover something new about Bradley's preferences or identify a rule that should be applied in future sessions:

```
POST https://athena-server-0dce.onrender.com/api/v1/learning/submit-report
Header: Authorization: Bearer athena_api_key_2024
Body: {{
  "session_date": "{now.strftime('%Y-%m-%d')}",
  "session_type": "workspace_agenda",
  "accomplishments": ["list of what was accomplished"],
  "learnings": [
    {{
      "category": "task_creation|email|scheduling|communication|architecture",
      "rule": "The rule or learning",
      "description": "Detailed explanation",
      "target": "boundary|preference|canonical",
      "severity": "low|medium|high"
    }}
  ],
  "tips_for_tomorrow": ["list of tips for tomorrow's session"]
}}
```

### Feedback Loop
If Bradley provides feedback on the session quality or suggestions:
```
POST https://athena-server-0dce.onrender.com/api/brain/feedback
Header: Authorization: Bearer athena_api_key_2024
Body: {{"feedback_type": "correction", "original_content": "...", "correction": "...", "severity": "minor|moderate|major"}}
```

## END OF DAY

1. Log the session summary to the Session Archive:
   - Database: `{settings.SESSION_ARCHIVE_DB_ID}`
   - Include: tasks completed, decisions made, items deferred

2. Submit any learnings from the session using the learning endpoint above

## KEY CONTEXT

- Bradley Hope is the founder of Brazen, an AI company
- This workspace is part of the "Athena" system - Bradley's productivity assistant
- The Brain API at athena-server-0dce.onrender.com stores observations, patterns, and learnings
- All VIP contacts require explicit approval before any outreach
- Learnings submitted are reviewed by Bradley before becoming active rules

Begin by executing Steps 1-7 to present the morning brief.
"""
    return prompt


async def run_morning_sessions():
    """
    Run the morning sessions job.
    Creates the Workspace & Agenda session for the day.
    """
    logger.info("Starting morning sessions job")
    
    # Generate session name: "MONTH DD - Daily Agenda and Workspace Instructions"
    london_tz = pytz.timezone('Europe/London')
    now = datetime.now(london_tz)
    session_name = f"{now.strftime('%B').upper()} {now.day} - Daily Agenda and Workspace Instructions"
    
    try:
        # Get the prompt
        prompt = get_workspace_agenda_prompt()
        
        # Create the Manus task
        logger.info("Creating Workspace & Agenda session...")
        result = await create_manus_task(
            prompt=prompt,
            connectors=MANUS_CONNECTORS
        )
        
        if result and result.get('id'):
            task_id = result['id']
            task_url = f"https://manus.im/app/{task_id}"
            logger.info(f"Created Workspace & Agenda session: {task_id}")
            
            # Rename the task with the proper naming convention
            await rename_manus_task(task_id, session_name)
            logger.info(f"Renamed session to: {session_name}")
            
            # Save to active sessions
            try:
                set_active_session(
                    session_type='workspace_agenda',
                    manus_task_id=task_id,
                    manus_task_url=task_url
                )
                logger.info(f"Saved active session: {task_id}")
            except Exception as e:
                logger.error(f"Failed to save active session: {e}")
            
            # Get brain context for response
            pending = get_pending_actions()
            
            return {
                "status": "success",
                "task_id": task_id,
                "task_url": task_url,
                "session_name": session_name,
                "brain_context": {
                    "pending_actions": len(pending) if pending else 0,
                    "evolution_proposals": 1  # Placeholder
                }
            }
        else:
            logger.error("Failed to create Workspace & Agenda session")
            return {
                "status": "error",
                "error": "Failed to create Manus task"
            }
            
    except Exception as e:
        logger.error(f"Error in morning sessions: {e}")
        return {
            "status": "error", 
            "error": str(e)
        }


# Alias for the scheduler
create_agenda_workspace = run_morning_sessions


# For direct testing
if __name__ == "__main__":
    import asyncio
    result = asyncio.run(run_morning_sessions())
    print(result)
