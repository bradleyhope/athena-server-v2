"""Integrations module."""
from .manus_api import (
    create_manus_task,
    rename_manus_task,
    create_athena_thinking_session,
    create_agenda_workspace_session,
    create_observation_burst_session,
    get_brain_system_prompt,
    LEGACY_SYSTEM_PROMPT
)
from .brain_context import (
    generate_brain_system_prompt,
    get_session_context_for_manus,
)
