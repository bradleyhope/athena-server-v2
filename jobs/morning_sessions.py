"""
Athena Server v2 - Morning Sessions Job
Creates ATHENA THINKING and Agenda & Workspace sessions via Manus API.
Stores session IDs in database for cross-session continuity.

Updated for Brain 2.0: Uses brain-driven system prompts and context.
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
from db.brain import (
    get_brain_status,
    get_pending_actions,
    get_evolution_proposals,
    update_session_state,
)

logger = logging.getLogger("athena.jobs.morning")


async def run_morning_sessions():
    """
    Main entry point for the morning sessions cron job.
    Creates both ATHENA THINKING and stores the session ID.
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
    
    # Create ATHENA THINKING session
    result = await create_athena_thinking()
    
    logger.info(f"Morning sessions job complete: {result}")
    return result


async def create_athena_thinking():
    """
    Create the daily ATHENA THINKING session.
    Triggered at 6:00 AM London time.
    Stores the session ID in the database for use throughout the day.
    
    Brain 2.0: Session now receives brain-driven system prompt.
    """
    logger.info("Creating ATHENA THINKING session...")
    
    # Log pre-session context
    pending_count = len(get_pending_actions())
    evolution_count = len(get_evolution_proposals())
    logger.info(f"Pre-session context: {pending_count} pending actions, {evolution_count} evolution proposals")
    
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
            
            # Update session state with creation info
            try:
                update_session_state(
                    session_type='athena_thinking',
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
            logger.error("Failed to create ATHENA THINKING session")
            return {"status": "error", "error": "Failed to create session"}
            
    except Exception as e:
        logger.error(f"Error creating ATHENA THINKING session: {e}")
        return {"status": "error", "error": str(e)}


async def create_agenda_workspace():
    """
    Create the daily Agenda & Workspace session for Bradley.
    Triggered at 6:05 AM London time.
    
    Brain 2.0: Session now receives brain-driven system prompt.
    """
    logger.info("Creating Agenda & Workspace session...")
    
    # Log pre-session context
    pending_count = len(get_pending_actions())
    evolution_count = len(get_evolution_proposals())
    logger.info(f"Pre-session context: {pending_count} pending actions, {evolution_count} evolution proposals")
    
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
            
            # Update session state
            try:
                update_session_state(
                    session_type='agenda_workspace',
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
            logger.error("Failed to create Agenda & Workspace session")
            return {"status": "error", "error": "Failed to create session"}
            
    except Exception as e:
        logger.error(f"Error creating Agenda & Workspace session: {e}")
        return {"status": "error", "error": str(e)}
