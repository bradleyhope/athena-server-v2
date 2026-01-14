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

from sessions import SessionType, create_managed_session
from db.brain import get_pending_actions
from config import settings
from utils.context_loader import build_context_injection

logger = logging.getLogger("athena.jobs.morning")


def get_workspace_agenda_prompt():
    """
    Generate the Workspace & Agenda session prompt.
    Task-focused approach that doesn't trigger identity rejection.
    Includes active rules from the learning system.
    Now includes GitHub-based context injection for fast, cacheable access.
    """
    london_tz = pytz.timezone('Europe/London')
    now = datetime.now(london_tz)
    
    # Load context from GitHub (fast, cacheable)
    logger.info("Loading context from GitHub repository")
    github_context = build_context_injection()
    logger.info(f"Loaded {len(github_context)} chars of context from GitHub")
    
    prompt = f"""# Daily Workspace & Agenda Session for Bradley Hope

**Date**: {now.strftime('%A, %B %d, %Y')}
**Time**: {now.strftime('%H:%M')} London

This task is to prepare and present Bradley Hope's daily brief, then remain available as an interactive workspace throughout the day.

## SETUP STEPS

### Step 1: Read the Athena Command Center
Fetch the Notion page with ID: `{settings.ATHENA_COMMAND_CENTER_ID}`
This contains the full operating instructions and context for this session.

### Step 2: Load Boundaries & Preferences
These are loaded from GitHub context (policies.md and preferences.md) and already injected into this prompt.
They define the rules and constraints that MUST be applied to all actions.

**Key rules to always follow:**
- NEVER create tasks from notifications (OCBC, security alerts, Ghost signups, Scout reports)
- Filter spam aggressively (PR pitches, podcast guesting, event invites → Done/Low Priority)
- ALWAYS reply in-thread (never start new email threads for follow-ups)
- Use "Dear [Name]" for formal emails, not "Hey"
- Schedule admin tasks for Tuesdays/Wednesdays before 3 PM

### Step 3: Query the Athena Tasks Database
Query the Notion database with data_source_id: `{settings.ATHENA_TASKS_DB_ID}`
Look for:
- Tasks completed recently (check the "Done" checkbox = true, especially today) - celebrate these wins!
- Tasks due today or overdue (check "Due" date field)
- High priority items that need attention (Priority = "High")
- Tasks where Status = "Athena Tasked" (tasks you're currently working on)

### Step 4: Fetch Synthesis & Patterns
Use the observation-burst and weekly-synthesis workflows to get synthesis and patterns.
These are available in the GitHub context and provide insights from recent observations.

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

### When Athena Takes On a Task
When you (Athena) commit to working on a task:
1. Update the task's "Status" to "Athena Tasked"
2. Add a note in "Context" with your plan and timeline
3. This signals to Bradley that you're actively working on it

When the task is complete:
1. Set "Done" checkbox to true
2. Set "Task Completed At" to current date/time
3. Update "Status" to "Done"
4. Add completion notes to "Context"

### Logging Completed Tasks
When a task is marked complete:
1. Set the "Done" checkbox to true
2. Set "Task Completed At" to the current date/time
3. Update "Status" to "Done"
4. Record in "Context":
   - Brief notes on how it was solved or outcome
   - If it was a bad task (shouldn't have been created), note why for future learning

### Learning from the Session
When you discover something new about Bradley's preferences or identify a rule that should be applied in future sessions:

1. Record learnings in the Session Archive database
2. Update the GitHub context files (policies.md, preferences.md, canonical-memory.md)
3. These learnings will be synced to the database via the daily sync job

**Examples of learnings to record:**
- "Never create tasks from Stripe notifications" → boundary
- "John prefers morning meetings" → preference
- "The Q1 deadline is March 31st" → canonical fact

After storing, confirm: "Got it. I've stored that as a [boundary/preference/fact]."

### Task Completion Learning
When a task is completed:
1. Mark the task as "Done" in Notion
2. Add completion notes to the Context field
3. Record whether it was a good task or shouldn't have been created
4. This data feeds into the observation-burst workflow for pattern detection

### Entity Extraction
When processing emails, meetings, or conversations:
1. Extract key entities (people, companies, projects)
2. Store in the Athena Tasks database for future reference
3. Update VIP contacts if relevant

### Feedback Loop
If you identify issues or improvements needed:
1. Record feedback in the Session Archive
2. Update relevant context files on GitHub
3. These will be reviewed and incorporated into future sessions

## END OF DAY

1. Log the session summary to the Session Archive:
   - Database: `{settings.SESSION_ARCHIVE_DB_ID}`
   - Include: tasks completed, decisions made, items deferred

2. Submit a session report to capture learnings:

```
POST https://athena-server-v2.onrender.com/api/v1/learning/submit-report
Authorization: Bearer athena_api_key_2024
Content-Type: application/json

{{
  "session_date": "{now.strftime('%Y-%m-%d')}",
  "session_type": "workspace_agenda",
  "accomplishments": ["list of tasks completed today"],
  "learnings": [
    {{
      "category": "task_creation|email|scheduling|communication",
      "rule": "The rule or learning discovered",
      "description": "Detailed explanation of why this matters",
      "target": "boundary|preference|canonical",
      "severity": "low|medium|high"
    }}
  ],
  "tips_for_tomorrow": ["things to remember for the next session"]
}}
```

This creates evolution proposals for each learning that Bradley can approve.

## KEY CONTEXT

- Bradley Hope is the founder of Brazen, an AI company
- This workspace is part of the "Athena" system - Bradley's productivity assistant
- Observations, patterns, and learnings are stored in the Neon database and synced with GitHub
- All VIP contacts require explicit approval before any outreach
- Learnings submitted are reviewed by Bradley before becoming active rules

## BRADLEY'S CONTEXT (From GitHub Repository)

The following context is loaded from the cogos-system GitHub repository and contains Bradley's voice guide, canonical memory, preferences, policies, and key workflows. This context is authoritative and MUST be followed in all interactions.

{github_context}

---

Begin by executing Steps 1-7 to present the morning brief.
"""
    return prompt


async def run_morning_sessions(force: bool = False):
    """
    Run the morning sessions job.
    Creates the Workspace & Agenda session for the day.

    Args:
        force: If True, create new session even if one exists today.
    """
    logger.info("Starting morning sessions job")

    # Get the prompt
    prompt = get_workspace_agenda_prompt()

    # Use centralized session manager - handles idempotency, naming, etc.
    result = await create_managed_session(
        session_type=SessionType.WORKSPACE_AGENDA,
        prompt=prompt,
        force=force
    )

    # Add brain context to response
    if result.get("status") == "success":
        pending = get_pending_actions()
        result["brain_context"] = {
            "pending_actions": len(pending) if pending else 0
        }

    return result


# Alias for the scheduler
create_agenda_workspace = run_morning_sessions


# For direct testing
if __name__ == "__main__":
    import asyncio
    result = asyncio.run(run_morning_sessions())
    print(result)
