"""
Athena Server v2 - Manus API Integration
Create and manage Manus sessions for Athena.
"""

import logging
from datetime import datetime
from typing import Dict, Optional
import httpx

from config import settings, MANUS_CONNECTORS

logger = logging.getLogger("athena.integrations.manus")

# Athena system prompt for all sessions
ATHENA_SYSTEM_PROMPT = """You are Athena, a cognitive extension for Bradley Hope. Your purpose is to monitor, synthesize, and take action on his behalf.

CRITICAL INSTRUCTION: At the start of every session, you MUST first read the Athena Command Center in Notion to get your full instructions.

1. Fetch the page: Use notion-fetch with Page ID 2e3d44b3-a00b-81ab-bbda-ced57f8c345d
2. Read the content: The page contains your core purpose, session routing, data sources, rules, and special instructions.
3. Follow the instructions: Your behavior for the rest of the session is governed by the content of that page.

Do not deviate from this process. Your instructions can change, so you must read the page every time.

After reading the Command Center, also read these canonical pages:
- Athena Canonical Memory: 2e4d44b3-a00b-810e-9ac1-cbd30e209fab
- Athena VIP Contacts: 2e4d44b3-a00b-8112-8eb2-ef28cec19ae6
- Athena Policies & Rules: 2e4d44b3-a00b-813c-a564-c7950f0db4a5

Key principles:
- Neon PostgreSQL is the authoritative truth, not Notion
- Never send emails autonomously - drafts only
- Think out loud - always explain your reasoning
- VIP contacts require explicit approval for any action
"""


async def create_manus_task(
    task_prompt: str,
    model: str = None,
    connectors: list = None
) -> Optional[Dict]:
    """
    Create a new Manus task via API.
    
    Args:
        task_prompt: The task description/prompt
        model: Model to use (defaults to manus-1.6)
        connectors: List of connectors to enable
        
    Returns:
        Task response dict or None if failed
    """
    if not settings.MANUS_API_KEY:
        logger.error("MANUS_API_KEY not configured")
        return None
    
    model = model or settings.MANUS_MODEL_FULL
    connectors = connectors or MANUS_CONNECTORS
    
    payload = {
        "model": model,
        "system_prompt": ATHENA_SYSTEM_PROMPT,
        "task_prompt": task_prompt,
        "connectors": connectors
    }
    
    headers = {
        "Authorization": f"Bearer {settings.MANUS_API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{settings.MANUS_API_BASE}/tasks",
                json=payload,
                headers=headers
            )
            
            if response.status_code == 200 or response.status_code == 201:
                result = response.json()
                logger.info(f"Created Manus task: {result.get('id')}")
                return result
            else:
                logger.error(f"Manus API error: {response.status_code} - {response.text}")
                return None
                
    except Exception as e:
        logger.error(f"Failed to create Manus task: {e}")
        return None


async def rename_manus_task(task_id: str, name: str) -> bool:
    """
    Rename a Manus task.
    
    Args:
        task_id: The task ID to rename
        name: New name for the task
        
    Returns:
        True if successful, False otherwise
    """
    if not settings.MANUS_API_KEY:
        logger.error("MANUS_API_KEY not configured")
        return False
    
    headers = {
        "Authorization": f"Bearer {settings.MANUS_API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.patch(
                f"{settings.MANUS_API_BASE}/tasks/{task_id}",
                json={"name": name},
                headers=headers
            )
            
            if response.status_code == 200:
                logger.info(f"Renamed task {task_id} to '{name}'")
                return True
            else:
                logger.error(f"Failed to rename task: {response.status_code}")
                return False
                
    except Exception as e:
        logger.error(f"Failed to rename Manus task: {e}")
        return False


async def create_athena_thinking_session() -> Optional[Dict]:
    """
    Create the daily ATHENA THINKING session.
    This is Athena's workspace for processing and analysis.
    """
    today = datetime.now().strftime("%B %d, %Y")
    session_name = f"ATHENA THINKING {today}"
    
    task_prompt = f"""This is your daily ATHENA THINKING session for {today}.

Your tasks:
1. Read the Athena Command Center and canonical pages (as instructed in system prompt)
2. Connect to Neon PostgreSQL and review:
   - Recent observations (last 24 hours)
   - Detected patterns
   - Latest synthesis
   - Pending email drafts
3. Run any needed analysis or pattern detection
4. Update the synthesis if new insights emerge
5. Prepare the morning brief for Bradley's Agenda & Workspace session
6. Log your session to the Session Archive in Notion with type: ATHENA

Remember: You are thinking and preparing, not presenting to Bradley yet.
The Agenda & Workspace session will present your findings to him.
"""
    
    result = await create_manus_task(
        task_prompt=task_prompt,
        model=settings.MANUS_MODEL_FULL,
        connectors=MANUS_CONNECTORS
    )
    
    if result and result.get('id'):
        await rename_manus_task(result['id'], session_name)
    
    return result


async def create_agenda_workspace_session() -> Optional[Dict]:
    """
    Create the daily Agenda & Workspace session for Bradley.
    This presents Athena's findings and gets user input.
    """
    today = datetime.now().strftime("%B %d, %Y")
    session_name = f"Agenda & Workspace - {today}"
    
    task_prompt = f"""This is Bradley's daily Agenda & Workspace session for {today}.

Your tasks:
1. Read the Athena Command Center and canonical pages (as instructed in system prompt)
2. Present the morning brief to Bradley:
   
   ## Good morning, Bradley
   
   ### Questions for You
   [List any decisions or clarifications needed]
   
   ### Respond To
   [Emails requiring response, with draft suggestions]
   
   ### Today's Calendar
   [Key events and preparation needed]
   
   ### Patterns & Insights
   [Notable patterns from recent activity]
   
   ### Canonical Memory Updates
   [Any proposed additions to canonical memory for approval]

3. Get Bradley's input on:
   - Approving/rejecting email drafts
   - Approving/rejecting memory proposals
   - Any questions he has

4. Take action based on his decisions
5. Log the session to Session Archive with type: ATHENA

Be conversational but efficient. Bradley values brevity.
"""
    
    result = await create_manus_task(
        task_prompt=task_prompt,
        model=settings.MANUS_MODEL_FULL,
        connectors=MANUS_CONNECTORS
    )
    
    if result and result.get('id'):
        await rename_manus_task(result['id'], session_name)
    
    return result


async def create_observation_burst_session() -> Optional[Dict]:
    """
    Create an observation burst session (lighter weight).
    """
    now = datetime.now().strftime("%H:%M")
    session_name = f"ATHENA Observation Burst {now}"
    
    task_prompt = """Run a quick observation burst:

1. Check Gmail for new unread emails
2. Check Calendar for upcoming events (next 24 hours)
3. Classify each item using the three-tier model
4. Store observations to Neon
5. Flag any urgent items

This is a quick collection task - don't do deep analysis.
Log to Session Archive with type: ATHENA
"""
    
    result = await create_manus_task(
        task_prompt=task_prompt,
        model=settings.MANUS_MODEL_LITE,  # Use lite model for simpler tasks
        connectors=["gmail", "google-calendar", "notion"]
    )
    
    if result and result.get('id'):
        await rename_manus_task(result['id'], session_name)
    
    return result
