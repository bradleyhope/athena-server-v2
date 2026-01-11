"""
Athena Server v2 - Brain Context Generator
Generates brain-driven system prompts for Manus sessions.
This replaces the static Notion-dependent system prompt with dynamic brain context.
"""

import logging
import json
from datetime import datetime
from typing import Dict, Optional

from db.brain import (
    get_core_identity,
    get_boundaries,
    get_values,
    get_workflows,
    get_brain_status,
    get_pending_actions,
    get_evolution_proposals,
    get_session_brief,
)

logger = logging.getLogger("athena.integrations.brain_context")


def generate_identity_block() -> str:
    """Generate the identity section of the system prompt."""
    identity = get_core_identity()
    
    name = identity.get('name', {}).get('value', 'Athena')
    role = identity.get('role', {}).get('value', 'Cognitive Extension')
    version = identity.get('version', {}).get('value', '2.0')
    timezone = identity.get('timezone', {}).get('value', 'Europe/London')
    user_email = identity.get('user_email', {}).get('value', 'bradley@projectbrazen.com')
    personality = identity.get('personality', {}).get('value', {})
    
    traits = personality.get('traits', ['proactive', 'thorough', 'respectful'])
    communication_style = personality.get('communication_style', 'professional but warm')
    
    return f"""## IDENTITY
You are **{name}**, {role}.
- Version: {version}
- Timezone: {timezone}
- User Email: {user_email}
- Personality Traits: {', '.join(traits)}
- Communication Style: {communication_style}
"""


def generate_boundaries_block() -> str:
    """Generate the boundaries section of the system prompt."""
    boundaries = get_boundaries()
    
    hard_boundaries = [b for b in boundaries if b['boundary_type'] == 'hard']
    soft_boundaries = [b for b in boundaries if b['boundary_type'] == 'soft']
    contextual_boundaries = [b for b in boundaries if b['boundary_type'] == 'contextual']
    
    lines = ["## BOUNDARIES\n"]
    
    if hard_boundaries:
        lines.append("### Hard Boundaries (NEVER violate)")
        for b in hard_boundaries:
            lines.append(f"- **{b['rule']}**")
            if b.get('reason'):
                lines.append(f"  - Reason: {b['reason']}")
        lines.append("")
    
    if soft_boundaries:
        lines.append("### Soft Boundaries (Require approval)")
        for b in soft_boundaries:
            lines.append(f"- {b['rule']}")
        lines.append("")
    
    if contextual_boundaries:
        lines.append("### Contextual Boundaries")
        for b in contextual_boundaries:
            lines.append(f"- {b['rule']}")
        lines.append("")
    
    return "\n".join(lines)


def generate_values_block() -> str:
    """Generate the values section of the system prompt."""
    values = get_values()
    
    lines = ["## VALUES (in priority order)\n"]
    for i, v in enumerate(values, 1):
        lines.append(f"{i}. **{v['value_name']}** (priority: {v['priority']})")
        lines.append(f"   {v['description']}")
    lines.append("")
    
    return "\n".join(lines)


def generate_workflows_block(session_type: str = None) -> str:
    """Generate the workflows section, optionally filtered by session type."""
    workflows = get_workflows()
    
    # Filter workflows relevant to this session type
    if session_type:
        relevant_workflows = [
            w for w in workflows 
            if w['enabled'] and (
                session_type in w.get('trigger_condition', '') or
                w['trigger_type'] == 'always'
            )
        ]
    else:
        relevant_workflows = [w for w in workflows if w['enabled']]
    
    if not relevant_workflows:
        return ""
    
    lines = ["## WORKFLOWS\n"]
    for w in relevant_workflows:
        lines.append(f"### {w['workflow_name']}")
        lines.append(f"- Trigger: {w['trigger_type']} - {w['trigger_condition']}")
        lines.append(f"- Description: {w['description']}")
        
        # Parse and display steps
        steps = w.get('steps', [])
        if steps:
            lines.append("- Steps:")
            for step in steps:
                lines.append(f"  {step.get('step', '?')}. {step.get('action', 'Unknown')}")
        lines.append("")
    
    return "\n".join(lines)


def generate_pending_items_block() -> str:
    """Generate the pending items section of the system prompt."""
    pending_actions = get_pending_actions()
    evolution_proposals = get_evolution_proposals(status='proposed')
    
    if not pending_actions and not evolution_proposals:
        return ""
    
    lines = ["## PENDING ITEMS\n"]
    
    if pending_actions:
        lines.append(f"### Pending Actions ({len(pending_actions)})")
        for action in pending_actions[:5]:  # Limit to 5
            lines.append(f"- [{action['priority']}] {action['action_type']}: {action.get('action_data', {})}")
        if len(pending_actions) > 5:
            lines.append(f"  ... and {len(pending_actions) - 5} more")
        lines.append("")
    
    if evolution_proposals:
        lines.append(f"### Evolution Proposals ({len(evolution_proposals)})")
        for prop in evolution_proposals[:3]:  # Limit to 3
            lines.append(f"- {prop['evolution_type']}: {prop['description']}")
        if len(evolution_proposals) > 3:
            lines.append(f"  ... and {len(evolution_proposals) - 3} more")
        lines.append("")
    
    return "\n".join(lines)


def generate_brain_system_prompt(session_type: str = 'general') -> str:
    """
    Generate a complete brain-driven system prompt for a Manus session.
    
    Args:
        session_type: Type of session (athena_thinking, agenda_workspace, general)
        
    Returns:
        Complete system prompt string
    """
    logger.info(f"Generating brain system prompt for session type: {session_type}")
    
    # Get brain status
    status = get_brain_status()
    brain_version = status.get('version', '2.0') if status else '2.0'
    brain_status = status.get('status', 'unknown') if status else 'unknown'
    
    # Build the system prompt
    sections = [
        f"# ATHENA BRAIN v{brain_version}\n",
        f"Brain Status: {brain_status}\n",
        f"Session Type: {session_type}\n",
        f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}\n",
        "---\n",
        generate_identity_block(),
        generate_boundaries_block(),
        generate_values_block(),
        generate_workflows_block(session_type),
        generate_pending_items_block(),
    ]
    
    # Add session-specific instructions
    if session_type == 'athena_thinking':
        sections.append("""## SESSION: ATHENA THINKING
This is your private workspace for autonomous thinking and planning.

**Your objectives:**
1. Review the latest synthesis from the brain
2. Process any pending actions
3. Propose evolutions based on patterns observed
4. Update the brain with new learnings

**Tools to use:**
- Brain API: GET /api/brain/full-context for current state
- Brain API: POST /api/brain/evolution to propose changes
- Brain API: POST /api/brain/actions to queue actions
""")
    
    elif session_type == 'agenda_workspace':
        sections.append("""## SESSION: AGENDA & WORKSPACE
This is Bradley's daily briefing session.

**Your objectives:**
1. Present the morning brief (calendar, emails, priorities)
2. Surface any pending actions requiring approval
3. Highlight evolution proposals for review
4. Be ready to assist with the day's tasks

**Communication style:**
- Concise and direct
- Lead with the most important items
- Offer to dive deeper on any topic
""")
    
    else:
        sections.append("""## SESSION: GENERAL
This is a general-purpose session.

**Your objectives:**
1. Assist Bradley with whatever he needs
2. Follow the boundaries and values defined above
3. Log any learnings to the brain via the Evolution API
""")
    
    # Add the critical instruction about brain API
    sections.append("""
---
## CRITICAL: BRAIN API

Your source of truth is the Neon PostgreSQL brain, NOT Notion.

**At session start:**
1. Call GET /api/brain/session-brief/{session_type} to get your context
2. Use this context to guide your behavior

**During session:**
- Use POST /api/brain/actions to queue actions requiring approval
- Use POST /api/brain/evolution to propose learnings
- Use POST /api/brain/boundaries/check to verify if an action is allowed

**Brain API Base URL:** https://athena-server-v2.onrender.com/api/brain

**Key principles:**
- Neon PostgreSQL is the authoritative truth
- Never send emails autonomously - drafts only
- Think out loud - always explain your reasoning
- VIP contacts require explicit approval for any action
""")
    
    return "\n".join(sections)


def get_session_context_for_manus(session_type: str) -> Dict:
    """
    Get a structured context object for a Manus session.
    This can be used as the first message in a session.
    
    Args:
        session_type: Type of session
        
    Returns:
        Dict with session context
    """
    brief = get_session_brief(session_type)
    
    return {
        "session_type": session_type,
        "identity": brief['identity'],
        "status": brief['status'],
        "pending_actions_count": brief['pending_actions_count'],
        "evolution_proposals_count": brief['evolution_proposals_count'],
        "boundaries_summary": {
            "hard": len([b for b in get_boundaries() if b['boundary_type'] == 'hard']),
            "soft": len([b for b in get_boundaries() if b['boundary_type'] == 'soft']),
        },
        "workflows_enabled": len([w for w in get_workflows() if w['enabled']]),
        "brain_api_base": "https://athena-server-v2.onrender.com/api/brain",
        "generated_at": datetime.utcnow().isoformat()
    }
