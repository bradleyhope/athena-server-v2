"""
Athena Server v2 - Teaching Session Job

A dedicated session for actively teaching Athena about Bradley's world.
Unlike the workspace session (task-focused), this is learning-focused.
"""

import logging
import pytz
from datetime import datetime
from typing import Dict, Any

from sessions import SessionType, create_managed_session
from db.brain import (
    get_boundaries,
    get_preferences,
    get_recent_impressions,
    get_vip_entities
)
from db.neon import db_cursor
from config import settings

logger = logging.getLogger("athena.jobs.teaching")


def get_teaching_session_prompt() -> str:
    """
    Generate the teaching session prompt.
    This is a dedicated session for Bradley to teach Athena.
    """
    london_tz = pytz.timezone('Europe/London')
    now = datetime.now(london_tz)

    # Get current knowledge state
    try:
        boundaries = get_boundaries()
        preferences = get_preferences()
        vip_entities = get_vip_entities()
    except Exception as e:
        logger.error(f"Failed to get brain context: {e}")
        boundaries = []
        preferences = []
        vip_entities = []

    # Count what we know
    boundary_count = len(boundaries) if boundaries else 0
    preference_count = len(preferences) if preferences else 0
    vip_count = len(vip_entities) if vip_entities else 0

    # Get recent learnings
    recent_learnings = []
    try:
        with db_cursor() as cursor:
            cursor.execute("""
                SELECT description, created_at FROM evolution_proposals
                WHERE status = 'approved'
                ORDER BY created_at DESC
                LIMIT 5
            """)
            recent_learnings = cursor.fetchall()
    except:
        pass

    recent_learnings_text = ""
    if recent_learnings:
        for learning in recent_learnings:
            recent_learnings_text += f"- {learning['description'][:100]}\n"
    else:
        recent_learnings_text = "- No recent learnings yet\n"

    return f"""# Athena Teaching Session

**Date**: {now.strftime('%A, %B %d, %Y at %H:%M')} London
**Purpose**: Bradley is going to teach me things about how to work better.

---

## WHAT I CURRENTLY KNOW

| Category | Count |
|----------|-------|
| Boundaries (rules) | {boundary_count} |
| Preferences | {preference_count} |
| VIP Contacts | {vip_count} |

### Recent Things I've Learned
{recent_learnings_text}

---

## HOW THIS SESSION WORKS

Bradley will tell me things. For each thing:

1. **Acknowledge** what I learned
2. **Ask ONE clarifying question** if needed
3. **Classify** it as:
   - **Boundary** (rule/constraint) - "Never...", "Always...", "Don't..."
   - **Preference** (how Bradley likes things) - "I prefer...", "Better to..."
   - **Fact** (information about the world) - "X is...", "Remember that..."
   - **Entity** (person/company/project info) - "John is...", "Project X..."
4. **Store it** using the appropriate endpoint
5. **Confirm** what was stored

---

## STORAGE ENDPOINTS

### For Boundaries (rules)
```
POST learn/quick
Header: Authorization: Bearer athena_api_key_2024
Body: {{"statement": "The rule", "source": "teaching_session"}}
```

### For Entity Information
```
POST v1/entities
Header: Authorization: Bearer athena_api_key_2024
Body: {{
  "entity_type": "person|organization|project",
  "name": "Name",
  "description": "Description",
  "metadata": {{"key": "value"}}
}}
```

### For VIP Status
```
PATCH v1/entities/{{id}}
Header: Authorization: Bearer athena_api_key_2024
Body: {{"access_tier": "vip"}}
```

### For Preferences
```
POST brain/preferences
Header: Authorization: Bearer athena_api_key_2024
Body: {{
  "category": "communication|scheduling|projects|general",
  "key": "preference_name",
  "value": "the preference"
}}
```

---

## TOPICS TO COVER

Prompt Bradley with these if conversation stalls:

### People & Relationships
- "Who are your VIP contacts that require approval before outreach?"
- "Who do you work with regularly?"
- "Any contacts I should know communication preferences for?"

### Projects & Work
- "What projects are you currently working on?"
- "What's the status of each project?"
- "What are the deadlines I should know about?"

### Communication Style
- "How do you prefer me to communicate?"
- "Any email formatting preferences?"
- "How should I handle different types of messages?"

### Schedule & Time
- "When do you prefer deep work vs meetings?"
- "Any blocked times I should know about?"
- "What days are best for what activities?"

### Rules & Boundaries
- "What should I never do?"
- "What always requires your approval?"
- "What can I do autonomously?"

---

## SESSION FLOW

1. **Opening**: "Hi Bradley! This is your teaching session. I'm ready to learn about your world. What would you like to teach me first?"

2. **Active Listening**: For each thing Bradley shares, follow the acknowledge → clarify → classify → store → confirm flow.

3. **Prompting**: If Bradley pauses, ask one question from the topics above.

4. **Summary**: At the end, summarize everything learned:
   - "Today I learned X boundaries, Y preferences, and Z facts about your world."
   - List the key things learned.

5. **Closing**: "These learnings are now stored. They'll apply to all my future sessions."

---

## IMPORTANT

- **Don't overwhelm** - Better to learn a few things well than many things poorly
- **Ask clarifying questions** - "When you say X, do you mean...?"
- **Confirm understanding** - "So if I understand correctly..."
- **Be specific** - Vague learnings are useless; make them actionable
- **Thank Bradley** - Learning takes time, appreciate it

---

**Begin by greeting Bradley and asking what he'd like to teach you first.**
"""


async def run_teaching_session(force: bool = False) -> Dict[str, Any]:
    """
    Run a teaching session for actively teaching Athena.

    Args:
        force: If True, create new session even if one exists today.

    Returns:
        Session result dict
    """
    logger.info("Starting teaching session")

    # Get the prompt
    prompt = get_teaching_session_prompt()

    # Use centralized session manager
    result = await create_managed_session(
        session_type=SessionType.TEACHING_SESSION,
        prompt=prompt,
        force=force
    )

    return result


# For direct testing
if __name__ == "__main__":
    import asyncio
    result = asyncio.run(run_teaching_session())
    print(result)
