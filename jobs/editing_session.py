"""
Athena Server v2 - Editing Session Job

A special session type for making safe changes to Athena's configuration,
boundaries, workflows, and capabilities. All changes go through the
evolution proposal system for approval.

This session is triggered manually when Bradley wants to discuss changes.
"""

import logging
import pytz
from datetime import datetime
from typing import Dict, Any, Optional

from sessions import SessionType, create_managed_session
from db.brain import (
    get_core_identity,
    get_boundaries,
    get_values,
    get_evolution_proposals,
    get_brain_status
)
from config import settings

logger = logging.getLogger("athena.jobs.editing")


def get_editing_session_prompt() -> str:
    """
    Generate the editing session prompt with full project context.
    This guides Manus to understand the codebase and make safe changes.
    """
    london_tz = pytz.timezone('Europe/London')
    now = datetime.now(london_tz)

    # Get current brain state
    try:
        identity = get_core_identity()
        boundaries = get_boundaries()
        values = get_values()
        pending_proposals = get_evolution_proposals()
        brain_status = get_brain_status()
    except Exception as e:
        logger.error(f"Failed to get brain context: {e}")
        identity = {}
        boundaries = []
        values = []
        pending_proposals = []
        brain_status = {}

    # Format boundaries for display
    boundaries_text = ""
    for b in boundaries[:10]:  # Limit to 10
        boundaries_text += f"- [{b.get('boundary_type', 'soft')}] {b.get('rule', '')}\n"

    # Format pending proposals
    proposals_text = ""
    pending_count = len([p for p in pending_proposals if p.get('status') == 'pending'])
    for p in pending_proposals[:5]:
        if p.get('status') == 'pending':
            proposals_text += f"- {p.get('proposal_type', 'unknown')}: {p.get('description', '')[:100]}\n"

    prompt = f"""# Athena Editing Session

**Date**: {now.strftime('%A, %B %d, %Y at %H:%M')} London
**Session Type**: System Configuration & Evolution

---

## WHAT THIS SESSION IS FOR

Bradley wants to discuss and potentially modify how Athena works. This is a **safe editing session** where all changes go through the proposal system before taking effect.

You can discuss and propose changes to:
- **Boundaries** - Rules about what Athena can/cannot do
- **Workflows** - How Athena handles specific tasks
- **Preferences** - Bradley's working style preferences
- **Capabilities** - What Athena can do

---

## CRITICAL SAFETY RULES

1. **ALL changes are PROPOSALS** - Nothing takes effect immediately
2. **Show before doing** - Always show the exact API call before executing
3. **Explain impact** - What will change and what could go wrong
4. **Bradley must approve** - Say "approved" or "do it" before any POST
5. **Code changes via GitHub** - Never modify code directly in this session

---

## ATHENA'S CURRENT STATE

### Core Identity
```
Name: Athena
Role: Cognitive Extension for Bradley Hope
Version: {brain_status.get('version', '2.0') if brain_status else '2.0'}
Status: {brain_status.get('status', 'active') if brain_status else 'active'}
```

### Active Boundaries ({len(boundaries)} total)
{boundaries_text if boundaries_text else "No boundaries loaded"}

### Pending Evolution Proposals ({pending_count})
{proposals_text if proposals_text else "No pending proposals"}

---

## PROJECT CONTEXT

### Codebase Location
**GitHub**: https://github.com/bradleyhope/athena-server-v2

### Key Documentation (Read these for context)
1. **Architecture Overview**: `docs/ATHENA_2.0_COMPLETE_ARCHITECTURE.md`
2. **Brain Architecture**: `docs/ATHENA_BRAIN_2.0_ARCHITECTURE.md`
3. **Session Guide**: `docs/SESSION_ARCHITECTURE.md`
4. **Workspace Guide**: `docs/WORKSPACE_AGENDA_GUIDE_UPDATE.md`

### Notion Databases
| Database | ID | Purpose |
|----------|-----|---------|
| Athena Tasks | `{settings.ATHENA_TASKS_DB_ID}` | Daily task management |
| Athena Brainstorm | `{settings.ATHENA_BRAINSTORM_DB_ID}` | Ideas and discoveries |
| Athena Projects | `{settings.ATHENA_PROJECTS_DB_ID}` | Project tracking |
| Broadcasts | `{settings.BROADCASTS_DATABASE_ID}` | Athena's broadcasts |
| Session Archive | `{settings.SESSION_ARCHIVE_DB_ID}` | Session logs |

### API Endpoints (Base: https://athena-server-0dce.onrender.com)
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/brain/status` | GET | Current brain status |
| `/api/brain/boundaries` | GET/POST | View/add boundaries |
| `/api/brain/preferences` | GET/POST | View/set preferences |
| `/api/brain/evolution` | POST | Submit evolution proposal |
| `/api/v1/evolution/proposals/pending` | GET | View pending proposals |
| `/api/v1/evolution/proposals/{{id}}/review` | POST | Approve/reject proposal |

**Auth Header**: `Authorization: Bearer athena_api_key_2024`

---

## HOW TO MAKE CHANGES

### Option 1: Add a Boundary
When Bradley says something like "Athena should never..." or "Always..."
```
POST /api/brain/boundaries
{{
  "boundary_type": "hard|soft|contextual",
  "category": "email|scheduling|communication|vip|financial",
  "rule": "The specific rule",
  "description": "Why this rule exists"
}}
```

### Option 2: Update a Preference
When Bradley expresses a preference about how things should work:
```
POST /api/brain/preferences
{{
  "category": "communication|scheduling|task_management",
  "key": "preference_name",
  "value": "the preference value"
}}
```

### Option 3: Submit Evolution Proposal
For larger changes that need review:
```
POST /api/brain/evolution
{{
  "proposal_type": "boundary|workflow|capability|architecture",
  "description": "What you want to change",
  "reasoning": "Why this would help",
  "impact": "What would be affected",
  "confidence": 0.8
}}
```

### Option 4: Request Code Changes
For actual code modifications:
1. Document the change needed
2. Create a GitHub issue at https://github.com/bradleyhope/athena-server-v2/issues
3. The change will be implemented and reviewed via PR

---

## SESSION WORKFLOW

1. **Listen** - Understand what Bradley wants to change
2. **Research** - Look up relevant docs, current state, implications
3. **Propose** - Show exactly what would change (the API call)
4. **Wait** - Don't execute until Bradley says "approved" or "do it"
5. **Execute** - Make the API call and confirm success
6. **Document** - Log what was changed and why

---

## STARTING THE SESSION

Begin by asking Bradley:
"What would you like to discuss or change about how I work? I can help with boundaries, preferences, workflows, or capabilities."

Then guide them through understanding the current state and safely making changes.

---

**Remember**: This is a collaborative editing session. Take your time, explain clearly, and never make changes without explicit approval.
"""
    return prompt


async def run_editing_session(force: bool = False) -> Dict[str, Any]:
    """
    Run an editing session for making safe changes to Athena.

    Args:
        force: If True, create new session even if one exists today.

    Returns:
        Session result dict
    """
    logger.info("Starting editing session")

    # Get the prompt
    prompt = get_editing_session_prompt()

    # Use centralized session manager - handles idempotency, naming, etc.
    result = await create_managed_session(
        session_type=SessionType.EDITING_SESSION,
        prompt=prompt,
        force=force
    )

    return result


# For direct testing
if __name__ == "__main__":
    import asyncio
    result = asyncio.run(run_editing_session())
    print(result)
