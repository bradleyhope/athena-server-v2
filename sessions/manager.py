"""
Athena Server v2 - Centralized Manus Session Manager

ALL Manus task creation MUST go through this module.
This ensures:
1. Only defined session types can be created
2. Naming conventions are enforced
3. Idempotency is guaranteed
4. No duplicate sessions
"""

import logging
from datetime import datetime, date
from typing import Dict, Any, Optional, List
from enum import Enum
import pytz

from db.neon import get_active_session, set_active_session
from integrations.manus_api import create_manus_task as _raw_create_manus_task
from integrations.manus_api import rename_manus_task
from config import MANUS_CONNECTORS

logger = logging.getLogger("athena.sessions.manager")


# =============================================================================
# Session Type Registry - ONLY these types can be created
# =============================================================================

class SessionType(Enum):
    """
    Registered session types. To add a new type:
    1. Add it here
    2. Add naming function in SESSION_NAMING
    3. Add idempotency rules in SESSION_IDEMPOTENCY
    """
    WORKSPACE_AGENDA = "workspace_agenda"
    ATHENA_THINKING = "athena_thinking"
    SYNTHESIS_BROADCAST = "synthesis_broadcast"
    EDITING_SESSION = "editing_session"
    TEACHING_SESSION = "teaching_session"
    # Add new types above this line


# Session naming conventions
def _name_workspace_agenda(now: datetime) -> str:
    return f"{now.strftime('%B').upper()} {now.day} - Daily Agenda and Workspace Instructions"

def _name_athena_thinking(now: datetime) -> str:
    return f"ATHENA THINKING {now.strftime('%B %d, %Y')}"

def _name_synthesis_broadcast(now: datetime) -> str:
    period = "Morning" if now.hour < 12 else "Evening"
    return f"Synthesis Broadcast - {period} {now.strftime('%B %d, %Y')}"

def _name_editing_session(now: datetime) -> str:
    return f"Athena Editing Session - {now.strftime('%B %d, %Y')}"

def _name_teaching_session(now: datetime) -> str:
    return f"Athena Teaching Session - {now.strftime('%B %d, %Y')}"


SESSION_NAMING = {
    SessionType.WORKSPACE_AGENDA: _name_workspace_agenda,
    SessionType.ATHENA_THINKING: _name_athena_thinking,
    SessionType.SYNTHESIS_BROADCAST: _name_synthesis_broadcast,
    SessionType.EDITING_SESSION: _name_editing_session,
    SessionType.TEACHING_SESSION: _name_teaching_session,
}


# Idempotency rules: how to determine if a session already exists
class IdempotencyRule(Enum):
    ONE_PER_DAY = "one_per_day"          # Only one session per calendar day
    ONE_PER_PERIOD = "one_per_period"    # One AM, one PM per day
    ALWAYS_NEW = "always_new"            # No idempotency (use sparingly!)


SESSION_IDEMPOTENCY = {
    SessionType.WORKSPACE_AGENDA: IdempotencyRule.ONE_PER_DAY,
    SessionType.ATHENA_THINKING: IdempotencyRule.ONE_PER_DAY,
    SessionType.SYNTHESIS_BROADCAST: IdempotencyRule.ONE_PER_PERIOD,
    SessionType.EDITING_SESSION: IdempotencyRule.ONE_PER_DAY,
    SessionType.TEACHING_SESSION: IdempotencyRule.ONE_PER_DAY,
}


# =============================================================================
# Session Manager
# =============================================================================

class SessionManager:
    """
    Centralized manager for all Manus session creation.

    Usage:
        manager = SessionManager()
        result = await manager.create_session(
            session_type=SessionType.WORKSPACE_AGENDA,
            prompt="...",
            force=False
        )
    """

    def __init__(self):
        self.london_tz = pytz.timezone('Europe/London')

    def _get_now(self) -> datetime:
        """Get current time in London timezone."""
        return datetime.now(self.london_tz)

    def _check_existing_session(
        self,
        session_type: SessionType,
        now: datetime,
        force: bool
    ) -> Optional[Dict[str, Any]]:
        """
        Check if a session already exists based on idempotency rules.

        Returns:
            Dict with existing session info if exists and shouldn't create new,
            None if should create new session.
        """
        if force:
            logger.info(f"Force=True, skipping idempotency check for {session_type.value}")
            return None

        existing = get_active_session(session_type.value)
        if not existing:
            return None

        existing_date = existing.get('session_date')
        today = now.date()

        rule = SESSION_IDEMPOTENCY.get(session_type, IdempotencyRule.ONE_PER_DAY)

        if rule == IdempotencyRule.ONE_PER_DAY:
            if existing_date == today:
                return {
                    "status": "already_exists",
                    "task_id": existing.get('manus_task_id'),
                    "task_url": existing.get('manus_task_url'),
                    "reason": f"Session already exists for today ({today})"
                }

        elif rule == IdempotencyRule.ONE_PER_PERIOD:
            if existing_date == today:
                # Check AM/PM
                existing_updated = existing.get('updated_at')
                if existing_updated:
                    existing_is_morning = existing_updated.hour < 12
                    current_is_morning = now.hour < 12
                    if existing_is_morning == current_is_morning:
                        period = "morning" if current_is_morning else "evening"
                        return {
                            "status": "already_exists",
                            "task_id": existing.get('manus_task_id'),
                            "task_url": existing.get('manus_task_url'),
                            "reason": f"Session already exists for {period} period"
                        }

        elif rule == IdempotencyRule.ALWAYS_NEW:
            pass  # Always create new

        return None

    async def create_session(
        self,
        session_type: SessionType,
        prompt: str,
        force: bool = False,
        connectors: List[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new Manus session with proper naming and idempotency.

        Args:
            session_type: Type of session (must be in SessionType enum)
            prompt: The prompt to send to Manus
            force: If True, create even if session exists
            connectors: List of connector IDs (defaults to MANUS_CONNECTORS)

        Returns:
            Dict with status, task_id, task_url, session_name
        """
        now = self._get_now()

        # Check for existing session
        existing = self._check_existing_session(session_type, now, force)
        if existing:
            logger.info(f"Session already exists: {existing['reason']}")
            return existing

        # Get naming function
        naming_func = SESSION_NAMING.get(session_type)
        if not naming_func:
            return {
                "status": "error",
                "error": f"No naming function for session type: {session_type.value}"
            }

        session_name = naming_func(now)

        logger.info(f"Creating Manus session: {session_type.value} -> {session_name}")

        try:
            # Create the Manus task
            result = await _raw_create_manus_task(
                prompt=prompt,
                connectors=connectors or MANUS_CONNECTORS
            )

            if not result or not result.get('id'):
                return {
                    "status": "error",
                    "error": "Failed to create Manus task - no ID returned"
                }

            task_id = result['id']
            task_url = f"https://manus.im/app/{task_id}"

            # Rename the task
            await rename_manus_task(task_id, session_name)
            logger.info(f"Renamed session to: {session_name}")

            # Save to active sessions
            set_active_session(
                session_type=session_type.value,
                task_id=task_id,
                task_url=task_url
            )

            logger.info(f"Session created successfully: {task_id}")

            return {
                "status": "success",
                "task_id": task_id,
                "task_url": task_url,
                "session_name": session_name,
                "session_type": session_type.value
            }

        except Exception as e:
            logger.error(f"Error creating session: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    def get_all_active(self) -> List[Dict[str, Any]]:
        """Get all active sessions."""
        from db.neon import get_all_active_sessions
        return get_all_active_sessions()


# Global instance
_manager = SessionManager()


# =============================================================================
# Public API - Use these functions instead of calling manus_api directly
# =============================================================================

async def create_managed_session(
    session_type: SessionType,
    prompt: str,
    force: bool = False,
    connectors: List[str] = None
) -> Dict[str, Any]:
    """
    Create a Manus session through the session manager.

    This is the ONLY way sessions should be created.
    """
    return await _manager.create_session(
        session_type=session_type,
        prompt=prompt,
        force=force,
        connectors=connectors
    )


def get_active_sessions() -> List[Dict[str, Any]]:
    """Get all active sessions."""
    return _manager.get_all_active()


def is_valid_session_type(type_name: str) -> bool:
    """Check if a session type name is valid."""
    try:
        SessionType(type_name)
        return True
    except ValueError:
        return False


def get_registered_session_types() -> List[str]:
    """Get list of all registered session types."""
    return [st.value for st in SessionType]
