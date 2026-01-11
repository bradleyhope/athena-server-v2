"""
Athena Server v2 - Manus API Integration
Create and manage Manus sessions for Athena.
Updated for Brain 2.0: Uses brain-driven system prompts instead of Notion.
"""

import logging
from datetime import datetime
from typing import Dict, Optional
import httpx

from config import settings, MANUS_CONNECTORS

logger = logging.getLogger("athena.integrations.manus")


def get_brain_system_prompt(session_type: str = 'general') -> str:
    """
    Get the brain-driven system prompt for a session.
    Falls back to legacy prompt if brain is unavailable.
    """
    try:
        from integrations.brain_context import generate_brain_system_prompt
        return generate_brain_system_prompt(session_type)
    except Exception as e:
        logger.warning(f"Failed to generate brain system prompt: {e}. Using legacy prompt.")
        return LEGACY_SYSTEM_PROMPT


# Legacy system prompt (fallback if brain is unavailable)
LEGACY_SYSTEM_PROMPT = """You are Athena, a cognitive extension for Bradley Hope. Your purpose is to monitor, synthesize, and take action on his behalf.

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
    connectors: list = None,
    session_type: str = 'general'
) -> Optional[Dict]:
    """
    Create a new Manus task via API.
    
    Args:
        task_prompt: The task description/prompt
        model: Model to use (defaults to manus-1.6)
        connectors: List of connectors to enable
        session_type: Type of session for brain context (athena_thinking, agenda_workspace, general)
        
    Returns:
        Task response dict or None if failed
    """
    if not settings.MANUS_API_KEY:
        logger.error("MANUS_API_KEY not configured")
        return None
    
    model = model or settings.MANUS_MODEL_FULL
    connectors = connectors or MANUS_CONNECTORS
    
    # Get brain-driven system prompt
    system_prompt = get_brain_system_prompt(session_type)
    
    # Combine system prompt and task prompt into single prompt
    # Manus API uses 'prompt' field, not 'system_prompt' + 'task_prompt'
    full_prompt = f"{system_prompt}\n\n---\n\n{task_prompt}"
    
    payload = {
        "model": model,
        "prompt": full_prompt,
        "connectors": connectors
    }
    
    headers = {
        "API_KEY": settings.MANUS_API_KEY,
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
                logger.info(f"Created Manus task: {result.get('id')} (session_type: {session_type})")
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
        "API_KEY": settings.MANUS_API_KEY,
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
    Now uses brain-driven system prompt.
    """
    today = datetime.now().strftime("%B %d, %Y")
    session_name = f"ATHENA THINKING {today}"
    
    task_prompt = f"""This is your daily ATHENA THINKING session for {today}.

## BRAIN 2.0 INITIALIZATION
Your context is loaded from the brain (Neon PostgreSQL). The system prompt contains your:
- Identity (who you are)
- Boundaries (what you can/cannot do)
- Values (how to make decisions)
- Workflows (how to accomplish tasks)

## YOUR TASKS
1. Call GET /api/brain/session-brief/athena_thinking to confirm your context
2. Connect to Neon PostgreSQL and review:
   - Recent observations (last 24 hours)
   - Detected patterns
   - Latest synthesis
   - Pending email drafts
3. Run any needed analysis or pattern detection
4. Update the synthesis if new insights emerge
5. Prepare the morning brief for Bradley's Agenda & Workspace session
6. Log any learnings via POST /api/brain/evolution

## BRAIN API
Base URL: https://athena-server-v2.onrender.com/api/brain
- GET /session-brief/athena_thinking - Your context
- GET /full-context - Complete brain state
- POST /evolution - Propose learnings
- POST /actions - Queue actions for approval

Remember: You are thinking and preparing, not presenting to Bradley yet.
The Agenda & Workspace session will present your findings to him.
"""
    
    result = await create_manus_task(
        task_prompt=task_prompt,
        model=settings.MANUS_MODEL_FULL,
        connectors=MANUS_CONNECTORS,
        session_type='athena_thinking'
    )
    
    if result and result.get('id'):
        await rename_manus_task(result['id'], session_name)
    
    return result


async def create_agenda_workspace_session() -> Optional[Dict]:
    """
    Create the daily Agenda & Workspace session for Bradley.
    This presents Athena's findings and gets user input.
    Now uses brain-driven system prompt.
    """
    today = datetime.now().strftime("%B %d, %Y")
    session_name = f"Agenda & Workspace - {today}"
    
    task_prompt = f"""This is Bradley's daily Agenda & Workspace session for {today}.

## BRAIN 2.0 INITIALIZATION
Your context is loaded from the brain (Neon PostgreSQL). The system prompt contains your:
- Identity (who you are)
- Boundaries (what you can/cannot do)
- Values (how to make decisions)
- Workflows (how to accomplish tasks)

## YOUR TASKS
1. Call GET /api/brain/session-brief/agenda_workspace to confirm your context
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
   
   ### Pending Approvals
   [Any pending actions or evolution proposals requiring approval]

3. Get Bradley's input on:
   - Approving/rejecting email drafts
   - Approving/rejecting evolution proposals
   - Any questions he has

4. Take action based on his decisions
5. Log feedback via POST /api/brain/feedback

## BRAIN API
Base URL: https://athena-server-v2.onrender.com/api/brain
- GET /session-brief/agenda_workspace - Your context
- GET /actions/pending - Pending actions
- GET /evolution?status=proposed - Evolution proposals
- POST /feedback - Log user feedback

Be conversational but efficient. Bradley values brevity.
"""
    
    result = await create_manus_task(
        task_prompt=task_prompt,
        model=settings.MANUS_MODEL_FULL,
        connectors=MANUS_CONNECTORS,
        session_type='agenda_workspace'
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

Brain API: https://athena-server-v2.onrender.com/api/brain
- POST /evolution to log any patterns noticed
"""
    
    result = await create_manus_task(
        task_prompt=task_prompt,
        model=settings.MANUS_MODEL_LITE,  # Use lite model for simpler tasks
        connectors=["gmail", "google-calendar", "notion"],
        session_type='general'
    )
    
    if result and result.get('id'):
        await rename_manus_task(result['id'], session_name)
    
    return result
