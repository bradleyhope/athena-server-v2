"""
Athena Server v2 - Passive Learning Extractor

Extracts entities, patterns, and learnings from any text/interaction.
Uses small LLM (GPT-4o-mini or Haiku) for cheap, fast extraction.
Runs automatically - no user prompts needed.
"""

import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from config import settings
from db.brain import (
    create_entity,
    get_entity_by_name,
    update_entity,
    add_entity_note,
    set_preference
)
from db.neon import db_cursor

logger = logging.getLogger("athena.learning.extractor")


# =============================================================================
# Entity Extraction
# =============================================================================

ENTITY_EXTRACTION_PROMPT = """Extract entities from this text. Return JSON only.

TEXT:
{text}

CONTEXT: {context}

Extract:
1. People mentioned (name, role/relationship if clear)
2. Companies/organizations mentioned
3. Projects mentioned
4. Topics/themes discussed
5. Any action items or commitments

Return JSON:
{{
  "people": [
    {{"name": "...", "role": "...", "context": "..."}}
  ],
  "companies": [
    {{"name": "...", "type": "...", "context": "..."}}
  ],
  "projects": [
    {{"name": "...", "status": "...", "context": "..."}}
  ],
  "topics": ["topic1", "topic2"],
  "action_items": ["item1", "item2"],
  "relationships": [
    {{"from": "...", "to": "...", "type": "..."}}
  ]
}}

If nothing found for a category, use empty array. Be conservative - only extract what's clearly mentioned.
"""


async def extract_entities_from_text(
    text: str,
    context: str = "",
    source: str = "unknown"
) -> Dict[str, Any]:
    """
    Extract entities from any text using a small LLM.

    Args:
        text: The text to analyze
        context: Additional context (e.g., "email from John", "task completion")
        source: Where this text came from

    Returns:
        Dict with extracted entities
    """
    if not text or len(text.strip()) < 10:
        return {"people": [], "companies": [], "projects": [], "topics": [], "action_items": [], "relationships": []}

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        response = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=1000,
            messages=[{
                "role": "user",
                "content": ENTITY_EXTRACTION_PROMPT.format(text=text[:2000], context=context)
            }]
        )

        # Parse JSON response
        response_text = response.content[0].text.strip()

        # Handle markdown code blocks
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]

        extracted = json.loads(response_text)
        extracted["source"] = source
        extracted["extracted_at"] = datetime.utcnow().isoformat()

        logger.info(f"Extracted {len(extracted.get('people', []))} people, "
                   f"{len(extracted.get('projects', []))} projects from {source}")

        return extracted

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse extraction response: {e}")
        return {"people": [], "companies": [], "projects": [], "topics": [], "action_items": [], "relationships": [], "error": str(e)}
    except Exception as e:
        logger.error(f"Entity extraction failed: {e}")
        return {"people": [], "companies": [], "projects": [], "topics": [], "action_items": [], "relationships": [], "error": str(e)}


async def store_extracted_entities(extracted: Dict[str, Any], source: str = "extraction") -> Dict[str, int]:
    """
    Store extracted entities in the brain.
    Creates new entities or updates existing ones.

    Returns:
        Dict with counts of created/updated entities
    """
    counts = {"people_created": 0, "people_updated": 0, "companies_created": 0, "projects_created": 0, "notes_added": 0}

    # Store people
    for person in extracted.get("people", []):
        name = person.get("name", "").strip()
        if not name or len(name) < 2:
            continue

        existing = get_entity_by_name(name)
        if existing:
            # Add a note about this mention
            add_entity_note(
                entity_id=existing["id"],
                note_type="mention",
                content=f"Mentioned in {source}: {person.get('context', '')}",
                importance=0.3
            )
            counts["notes_added"] += 1
            counts["people_updated"] += 1
        else:
            # Create new entity
            create_entity(
                entity_type="person",
                name=name,
                description=person.get("role", ""),
                metadata={
                    "first_seen": datetime.utcnow().isoformat(),
                    "source": source,
                    "context": person.get("context", "")
                },
                source=source
            )
            counts["people_created"] += 1

    # Store companies
    for company in extracted.get("companies", []):
        name = company.get("name", "").strip()
        if not name or len(name) < 2:
            continue

        existing = get_entity_by_name(name)
        if not existing:
            create_entity(
                entity_type="organization",
                name=name,
                description=company.get("type", ""),
                metadata={
                    "first_seen": datetime.utcnow().isoformat(),
                    "source": source,
                    "context": company.get("context", "")
                },
                source=source
            )
            counts["companies_created"] += 1

    # Store projects
    for project in extracted.get("projects", []):
        name = project.get("name", "").strip()
        if not name or len(name) < 2:
            continue

        existing = get_entity_by_name(name)
        if not existing:
            create_entity(
                entity_type="project",
                name=name,
                description=project.get("status", ""),
                metadata={
                    "first_seen": datetime.utcnow().isoformat(),
                    "source": source,
                    "context": project.get("context", "")
                },
                source=source
            )
            counts["projects_created"] += 1

    logger.info(f"Stored entities: {counts}")
    return counts


# =============================================================================
# Task Completion Learning
# =============================================================================

TASK_LEARNING_PROMPT = """Analyze this completed task and extract learnings.

TASK: {task_title}
COMPLETION NOTES: {completion_notes}
TIME TAKEN: {time_taken}
CONTEXT: {context}

Extract:
1. How was this task accomplished? (method/approach)
2. Who was involved?
3. What tools/resources were used?
4. Any patterns or preferences revealed?
5. Should this become a workflow for similar tasks?

Return JSON:
{{
  "method": "How it was done",
  "people_involved": ["person1", "person2"],
  "tools_used": ["tool1", "tool2"],
  "learnings": [
    {{"type": "preference|pattern|workflow", "content": "...", "confidence": 0.8}}
  ],
  "should_create_workflow": true/false,
  "workflow_suggestion": "If true, describe the workflow"
}}
"""


async def learn_from_task_completion(
    task_title: str,
    completion_notes: str = "",
    time_taken: str = "",
    context: str = "",
    was_good_task: bool = True
) -> Dict[str, Any]:
    """
    Extract learnings from a completed task.

    Args:
        task_title: What the task was
        completion_notes: Notes about how it was done
        time_taken: How long it took
        context: Additional context
        was_good_task: If False, learn what NOT to create

    Returns:
        Dict with extracted learnings
    """
    if not was_good_task:
        # Learn from bad tasks - what NOT to do
        return await learn_from_bad_task(task_title, completion_notes)

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        response = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=800,
            messages=[{
                "role": "user",
                "content": TASK_LEARNING_PROMPT.format(
                    task_title=task_title,
                    completion_notes=completion_notes or "No notes",
                    time_taken=time_taken or "Unknown",
                    context=context or "No additional context"
                )
            }]
        )

        response_text = response.content[0].text.strip()

        # Handle markdown code blocks
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]

        learnings = json.loads(response_text)
        learnings["task_title"] = task_title
        learnings["learned_at"] = datetime.utcnow().isoformat()

        # Store learnings
        await store_task_learnings(learnings)

        return learnings

    except Exception as e:
        logger.error(f"Task learning failed: {e}")
        return {"error": str(e)}


async def learn_from_bad_task(task_title: str, reason: str = "") -> Dict[str, Any]:
    """
    Learn from a task that shouldn't have been created.
    Creates a boundary to prevent similar tasks.
    """
    learning = {
        "type": "bad_task",
        "task_title": task_title,
        "reason": reason,
        "learned_at": datetime.utcnow().isoformat(),
        "proposed_boundary": f"Do not create tasks like: {task_title}"
    }

    # Store as pending boundary proposal
    with db_cursor() as cursor:
        cursor.execute("""
            INSERT INTO evolution_proposals (
                proposal_type, category, description, reasoning, status, confidence
            ) VALUES (
                'boundary', 'task_creation', %s, %s, 'pending', 0.7
            )
        """, (
            f"Avoid creating tasks like: {task_title}",
            f"Task was marked as bad. Reason: {reason or 'Not specified'}"
        ))

    logger.info(f"Learned from bad task: {task_title}")
    return learning


async def store_task_learnings(learnings: Dict[str, Any]) -> None:
    """Store learnings from task completion."""

    # Store any preferences discovered
    for learning in learnings.get("learnings", []):
        if learning.get("type") == "preference" and learning.get("confidence", 0) > 0.6:
            # High confidence preference - store directly
            set_preference(
                category="task_patterns",
                key=f"learned_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                value=learning.get("content", ""),
                source="task_completion"
            )

    # Store workflow suggestion if any
    if learnings.get("should_create_workflow") and learnings.get("workflow_suggestion"):
        with db_cursor() as cursor:
            cursor.execute("""
                INSERT INTO evolution_proposals (
                    proposal_type, category, description, reasoning, status, confidence
                ) VALUES (
                    'workflow', 'task_patterns', %s, %s, 'pending', 0.6
                )
            """, (
                learnings.get("workflow_suggestion"),
                f"Extracted from task: {learnings.get('task_title')}"
            ))


# =============================================================================
# Quick Learn - Explicit Learning
# =============================================================================

async def quick_learn(
    statement: str,
    source: str = "quick_learn"
) -> Dict[str, Any]:
    """
    Process a quick learn statement like "Learn: Never create tasks from Stripe notifications"

    Args:
        statement: The thing to learn (without "Learn:" prefix)
        source: Where this came from

    Returns:
        Dict with what was learned and where it was stored
    """
    statement = statement.strip()
    if statement.lower().startswith("learn:"):
        statement = statement[6:].strip()
    if statement.lower().startswith("remember:"):
        statement = statement[9:].strip()

    # Classify what type of learning this is
    classification = await classify_learning(statement)

    result = {
        "statement": statement,
        "classification": classification,
        "stored": False,
        "storage_location": None
    }

    if classification["type"] == "boundary":
        # Store as boundary
        with db_cursor() as cursor:
            cursor.execute("""
                INSERT INTO boundaries (boundary_type, category, rule, description, active)
                VALUES ('soft', %s, %s, %s, true)
                RETURNING id
            """, (classification.get("category", "general"), statement, f"Quick learned on {datetime.utcnow().isoformat()}"))
            result["stored"] = True
            result["storage_location"] = "boundaries"
            result["id"] = cursor.fetchone()["id"]

    elif classification["type"] == "preference":
        # Store as preference
        set_preference(
            category=classification.get("category", "general"),
            key=f"quick_learn_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            value=statement,
            source=source
        )
        result["stored"] = True
        result["storage_location"] = "preferences"

    elif classification["type"] == "fact":
        # Store in canonical memory
        with db_cursor() as cursor:
            cursor.execute("""
                INSERT INTO canonical_memory (category, key, value, content, source, confidence)
                VALUES (%s, %s, %s, %s, %s, 0.9)
                RETURNING id
            """, (
                classification.get("category", "facts"),
                f"quick_learn_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                statement,  # value column (required)
                statement,  # content column (for display)
                source
            ))
            result["stored"] = True
            result["storage_location"] = "canonical_memory"
            result["id"] = cursor.fetchone()["id"]

    logger.info(f"Quick learned: {statement} -> {result['storage_location']}")
    return result


async def classify_learning(statement: str) -> Dict[str, Any]:
    """
    Classify a learning statement into boundary/preference/fact.
    """
    # Simple rule-based classification first
    statement_lower = statement.lower()

    # Boundary indicators
    if any(word in statement_lower for word in ["never", "don't", "always", "must", "forbidden", "required"]):
        category = "general"
        if "email" in statement_lower:
            category = "email"
        elif "task" in statement_lower:
            category = "task_creation"
        elif "calendar" in statement_lower or "meeting" in statement_lower:
            category = "scheduling"
        return {"type": "boundary", "category": category}

    # Preference indicators
    if any(word in statement_lower for word in ["prefer", "like", "want", "better", "rather"]):
        category = "general"
        if "email" in statement_lower or "communication" in statement_lower:
            category = "communication"
        elif "schedule" in statement_lower or "time" in statement_lower:
            category = "scheduling"
        return {"type": "preference", "category": category}

    # Default to fact
    return {"type": "fact", "category": "facts"}


# =============================================================================
# Context Tracking
# =============================================================================

async def update_working_context(
    current_focus: str = None,
    active_project: str = None,
    blocked_on: str = None,
    energy_level: str = None
) -> Dict[str, Any]:
    """
    Update Bradley's current working context.
    This is called periodically or when context changes.
    """
    context = {}

    with db_cursor() as cursor:
        if current_focus:
            cursor.execute("""
                INSERT INTO session_state (session_type, session_date, state_data)
                VALUES ('working_context', CURRENT_DATE, %s)
                ON CONFLICT (session_type, session_date) DO UPDATE SET
                    state_data = session_state.state_data || %s,
                    updated_at = NOW()
            """, (
                json.dumps({"current_focus": current_focus}),
                json.dumps({"current_focus": current_focus})
            ))
            context["current_focus"] = current_focus

        if active_project:
            context["active_project"] = active_project

        if blocked_on:
            context["blocked_on"] = blocked_on

    return {"updated": True, "context": context}


def get_current_context() -> Dict[str, Any]:
    """Get Bradley's current working context."""
    with db_cursor() as cursor:
        cursor.execute("""
            SELECT state_data FROM session_state
            WHERE session_type = 'working_context'
            AND session_date = CURRENT_DATE
            ORDER BY updated_at DESC
            LIMIT 1
        """)
        row = cursor.fetchone()
        if row:
            return row["state_data"] if isinstance(row["state_data"], dict) else json.loads(row["state_data"])
        return {}
