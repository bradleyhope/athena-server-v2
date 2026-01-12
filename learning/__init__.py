"""
Athena Server v2 - Learning Module

Passive and active learning from all interactions.

Usage:
    from learning import extract_entities_from_text, quick_learn, learn_from_task_completion

    # Passive: Extract entities from any text
    entities = await extract_entities_from_text(email_body, context="email from client")

    # Active: Quick learn from explicit statement
    result = await quick_learn("Never create tasks from Stripe notifications")

    # Task: Learn from completed task
    learnings = await learn_from_task_completion(task_title, completion_notes)
"""

from learning.extractor import (
    extract_entities_from_text,
    store_extracted_entities,
    learn_from_task_completion,
    learn_from_bad_task,
    quick_learn,
    classify_learning,
    update_working_context,
    get_current_context,
)

__all__ = [
    "extract_entities_from_text",
    "store_extracted_entities",
    "learn_from_task_completion",
    "learn_from_bad_task",
    "quick_learn",
    "classify_learning",
    "update_working_context",
    "get_current_context",
]
