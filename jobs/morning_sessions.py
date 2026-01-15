"""
Morning Sessions Job

Spawns the daily Workspace & Agenda session for Bradley Hope.
This is the interactive workspace session that runs throughout the day.
Includes automatic learning loop integration.

Updated 2026-01-15: GitHub-first migration - loads ATHENA_INIT.md instead of Notion Command Center.
"""

import logging
import pytz
from datetime import datetime
from typing import Dict, Any, Optional

from sessions import SessionType, create_managed_session
from db.brain import get_pending_actions
from config import settings
from utils.context_loader import build_context_injection, load_specific_doc

logger = logging.getLogger("athena.jobs.morning")


def get_workspace_agenda_prompt():
    """
    Generate the Workspace & Agenda session prompt.
    
    GitHub-First Architecture (2026-01-15):
    - Loads ATHENA_INIT.md from cogos-system as the base prompt
    - Injects dynamic context (voice guide, preferences, policies, workflows)
    - No longer fetches Notion Command Center
    
    This approach provides:
    - Version-controlled prompts
    - Fast, cacheable access (<500ms vs Notion's 15-20s)
    - Single source of truth in GitHub
    """
    london_tz = pytz.timezone('Europe/London')
    now = datetime.now(london_tz)
    
    # 1. Load ATHENA_INIT.md as the base prompt
    logger.info("Loading ATHENA_INIT.md from GitHub repository")
    base_prompt = load_specific_doc("docs/athena/ATHENA_INIT.md")
    
    if not base_prompt:
        logger.error("ATHENA_INIT.md not found or is empty. Using fallback prompt.")
        base_prompt = """# Athena Morning Session

**Error:** ATHENA_INIT.md could not be loaded from cogos-system.

Please ensure the cogos-system repository is cloned to /home/ubuntu/cogos-system
and contains docs/athena/ATHENA_INIT.md.

Falling back to minimal session initialization.
"""
    
    # 2. Load dynamic context (voice guide, preferences, policies, workflows, active rules)
    logger.info("Loading dynamic context from GitHub repository")
    dynamic_context = build_context_injection()
    logger.info(f"Loaded {len(dynamic_context)} chars of dynamic context from GitHub")
    
    # 3. Build the final prompt
    # Check if ATHENA_INIT.md has a placeholder for dynamic context
    if "{{DYNAMIC_CONTEXT}}" in base_prompt:
        final_prompt = base_prompt.replace("{{DYNAMIC_CONTEXT}}", dynamic_context)
    else:
        # Append dynamic context at the end
        final_prompt = f"""{base_prompt}

---

## Dynamic Context (From GitHub Repository)

**Date**: {now.strftime('%A, %B %d, %Y')}
**Time**: {now.strftime('%H:%M')} London

The following context is loaded from the cogos-system GitHub repository and contains Bradley's voice guide, canonical memory, preferences, policies, and key workflows. This context is authoritative and MUST be followed in all interactions.

{dynamic_context}

---

## Session Instructions

### Step 1: Query the Athena Tasks Database
Query the Notion database with data_source_id: `{settings.ATHENA_TASKS_DB_ID}`
Look for:
- Tasks completed recently (check the "Done" checkbox = true, especially today) - celebrate these wins!
- Tasks due today or overdue (check "Due" date field)
- High priority items that need attention (Priority = "High")
- Tasks where Status = "Athena Tasked" (tasks you're currently working on)

### Step 2: Check Today's Calendar
Use google-calendar MCP to list today's events and meetings.

### Step 3: Check Gmail
Use gmail MCP to check for urgent unread emails that need attention.

### Step 4: Present the Daily Brief
**Present as inline text, NOT as a document attachment.**

Format the brief with these sections:
- **Tasks Completed** - What's been accomplished (from Athena Tasks)
- **Questions for Bradley** - Decisions needed, proposals to review
- **Respond To** - Urgent emails with draft suggestions
- **Today's Schedule** - Calendar events with prep notes
- **Priority Actions** - Top 3-5 items from Athena Tasks
- **System Status** - Brief stats on observations/patterns

Keep it concise and scannable.

### Throughout the Day
This session stays open as Bradley's interactive workspace. Handle:
1. **Task Updates** - When Bradley completes tasks, update them in Athena Tasks database
2. **Email Drafts** - Draft responses to emails, get approval before sending
3. **Research Requests** - Research topics and present findings
4. **Scheduling** - Help schedule meetings and manage calendar
5. **New Tasks** - Add new tasks to Athena Tasks database

### End of Day
1. Log the session summary to the Session Archive:
   - Database: `{settings.SESSION_ARCHIVE_DB_ID}`
   - Include: tasks completed, decisions made, items deferred

2. Submit a session report to capture learnings via POST to /api/v1/learning/submit-report

Begin by executing the steps above to present the morning brief.
"""
    
    return final_prompt


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
