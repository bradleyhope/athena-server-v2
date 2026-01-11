"""
Athena Server v2 - Manus API Integration
Create and manage Manus sessions for Athena.

LEAN PROMPT APPROACH:
- Minimal system context in the prompt itself
- Athena fetches her own context from Notion/Brain API during session
- Task prompts are short and action-oriented
"""

import logging
from datetime import datetime
from typing import Dict, Optional
import httpx

from config import settings, MANUS_CONNECTORS

logger = logging.getLogger("athena.integrations.manus")


async def create_manus_task(
    prompt: str = None,
    task_prompt: str = None,
    model: str = None,
    connectors: list = None,
    session_type: str = 'general'
) -> Optional[Dict]:
    """
    Create a new Manus task via API.
    
    Uses LEAN prompts - the task prompt IS the full prompt.
    No additional system prompt is prepended.
    
    Args:
        prompt: The task description/prompt (preferred)
        task_prompt: Alias for prompt (backwards compatibility)
        model: Model to use (defaults to manus-1.6)
        connectors: List of connectors to enable
        session_type: Type of session (for logging only)
        
    Returns:
        Task response dict or None if failed
    """
    if not settings.MANUS_API_KEY:
        logger.error("MANUS_API_KEY not configured")
        return None
    
    # Support both 'prompt' and 'task_prompt' parameter names
    actual_prompt = prompt or task_prompt
    if not actual_prompt:
        logger.error("No prompt provided to create_manus_task")
        return None
    
    model = model or settings.MANUS_MODEL_FULL
    connectors = connectors or MANUS_CONNECTORS
    
    # LEAN APPROACH: Use the task prompt directly, no system prompt prepended
    payload = {
        "model": model,
        "prompt": actual_prompt,
        "connectors": connectors
    }
    
    headers = {
        "API_KEY": settings.MANUS_API_KEY,
        "Content-Type": "application/json"
    }
    
    logger.info(f"Creating Manus task: model={model}, session_type={session_type}, prompt_length={len(actual_prompt)}")
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{settings.MANUS_API_BASE}/tasks",
                json=payload,
                headers=headers
            )
            
            logger.info(f"Manus API response: status={response.status_code}")
            
            if response.status_code == 200 or response.status_code == 201:
                result = response.json()
                # Normalize response - API returns task_id, we use id internally
                if 'task_id' in result and 'id' not in result:
                    result['id'] = result['task_id']
                logger.info(f"Created Manus task: {result.get('id')} (session_type: {session_type})")
                return result
            else:
                logger.error(f"Manus API error: {response.status_code} - {response.text}")
                return None
                
    except httpx.TimeoutException as e:
        logger.error(f"Manus API timeout: {e}")
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
