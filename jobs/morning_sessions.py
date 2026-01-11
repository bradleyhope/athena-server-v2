"""
Athena Server v2 - Morning Sessions Job
Creates ATHENA THINKING and Agenda & Workspace sessions via Manus API.
Stores session IDs in database for cross-session continuity.
"""

import logging
from datetime import datetime

from integrations.manus_api import (
    create_athena_thinking_session,
    create_agenda_workspace_session
)
from db.neon import (
    ensure_active_sessions_table,
    set_active_session,
    get_todays_thinking_session
)

logger = logging.getLogger("athena.jobs.morning")


async def run_morning_sessions():
    """
    Main entry point for the morning sessions cron job.
    Creates both ATHENA THINKING and stores the session ID.
    """
    logger.info("Starting morning sessions job...")
    
    # Ensure the active_sessions table exists
    try:
        ensure_active_sessions_table()
    except Exception as e:
        logger.warning(f"Could not ensure active_sessions table: {e}")
    
    # Create ATHENA THINKING session
    result = await create_athena_thinking()
    
    logger.info(f"Morning sessions job complete: {result}")
    return result


async def create_athena_thinking():
    """
    Create the daily ATHENA THINKING session.
    Triggered at 6:00 AM London time.
    Stores the session ID in the database for use throughout the day.
    """
    logger.info("Creating ATHENA THINKING session...")
    
    try:
        result = await create_athena_thinking_session()
        
        if result:
            task_id = result.get('id')
            task_url = f"https://manus.im/app/{task_id}"
            
            logger.info(f"ATHENA THINKING session created: {task_id}")
            
            # Store in database for cross-session access
            try:
                set_active_session(
                    session_type='athena_thinking',
                    task_id=task_id,
                    task_url=task_url
                )
                logger.info(f"Stored active session in database: athena_thinking = {task_id}")
            except Exception as db_error:
                logger.error(f"Failed to store session in database: {db_error}")
            
            return {
                "status": "success", 
                "task_id": task_id,
                "task_url": task_url
            }
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
            task_id = result.get('id')
            task_url = f"https://manus.im/app/{task_id}"
            
            logger.info(f"Agenda & Workspace session created: {task_id}")
            
            # Store in database
            try:
                set_active_session(
                    session_type='agenda_workspace',
                    task_id=task_id,
                    task_url=task_url
                )
            except Exception as db_error:
                logger.error(f"Failed to store session in database: {db_error}")
            
            return {
                "status": "success", 
                "task_id": task_id,
                "task_url": task_url
            }
        else:
            logger.error("Failed to create Agenda & Workspace session")
            return {"status": "error", "error": "Failed to create session"}
            
    except Exception as e:
        logger.error(f"Error creating Agenda & Workspace session: {e}")
        return {"status": "error", "error": str(e)}
