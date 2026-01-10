"""
Athena Server v2 - Morning Sessions Job
Creates ATHENA THINKING and Agenda & Workspace sessions via Manus API.
"""

import logging
from datetime import datetime

from integrations.manus_api import (
    create_athena_thinking_session,
    create_agenda_workspace_session
)

logger = logging.getLogger("athena.jobs.morning")


async def create_athena_thinking():
    """
    Create the daily ATHENA THINKING session.
    Triggered at 6:00 AM London time.
    """
    logger.info("Creating ATHENA THINKING session...")
    
    try:
        result = await create_athena_thinking_session()
        
        if result:
            logger.info(f"ATHENA THINKING session created: {result.get('id')}")
            return {"status": "success", "task_id": result.get('id')}
        else:
            logger.error("Failed to create ATHENA THINKING session")
            return {"status": "error", "error": "Failed to create session"}
            
    except Exception as e:
        logger.error(f"Error creating ATHENA THINKING session: {e}")
        return {"status": "error", "error": str(e)}


async def create_agenda_workspace():
    """
    Create the daily Agenda & Workspace session.
    Triggered at 6:05 AM London time.
    """
    logger.info("Creating Agenda & Workspace session...")
    
    try:
        result = await create_agenda_workspace_session()
        
        if result:
            logger.info(f"Agenda & Workspace session created: {result.get('id')}")
            return {"status": "success", "task_id": result.get('id')}
        else:
            logger.error("Failed to create Agenda & Workspace session")
            return {"status": "error", "error": "Failed to create session"}
            
    except Exception as e:
        logger.error(f"Error creating Agenda & Workspace session: {e}")
        return {"status": "error", "error": str(e)}
