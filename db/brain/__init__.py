"""
Athena Brain - Database Layer

Four-layer architecture for Athena's cognitive functions:
- Layer 1: Identity (core identity, boundaries, values)
- Layer 2: Knowledge (workflows, preferences)
- Layer 3: State (context windows, pending actions, session state)
- Layer 4: Evolution (proposals, metrics, feedback)
- Status: Brain status and Notion sync tracking
- Composite: Complex queries spanning multiple layers, entities, impressions
"""

# Layer 1: Identity
from db.brain.identity import (
    get_core_identity,
    get_identity_value,
    update_identity_value,
    get_boundaries,
    check_boundary,
    get_values,
)

# Layer 2: Knowledge
from db.brain.knowledge import (
    get_workflows,
    get_workflow,
    update_workflow_execution,
    create_workflow,
    get_preferences,
    get_preference,
    set_preference,
)

# Layer 3: State
from db.brain.state import (
    get_context_window,
    set_context_window,
    clear_context_windows,
    get_pending_actions,
    create_pending_action,
    approve_pending_action,
    reject_pending_action,
    execute_pending_action,
    get_session_state,
    set_session_state,
    update_session_state,
)

# Layer 4: Evolution
from db.brain.evolution import (
    log_evolution,
    get_evolution_proposals,
    approve_evolution,
    apply_evolution,
    record_metric,
    get_metrics,
    record_performance_metric,
    record_feedback,
    get_unprocessed_feedback,
    mark_feedback_processed,
)

# Status
from db.brain.status import (
    get_brain_status,
    update_brain_status,
    record_synthesis_time,
    record_evolution_time,
    record_notion_sync_time,
    log_notion_sync,
    update_notion_sync_status,
    get_pending_notion_syncs,
)

# Composite queries
from db.brain.composite import (
    get_full_brain_context,
    get_session_brief,
    # Daily impressions
    store_daily_impression,
    store_daily_impressions_batch,
    get_recent_impressions,
    get_todays_impressions,
    # Continuous state
    get_recent_sessions,
    get_recent_observations,
    get_recent_patterns,
    get_recent_synthesis,
    get_continuous_state_context,
    # Entities
    create_entity,
    get_entity,
    get_entity_by_name,
    search_entities,
    get_entities_by_type,
    get_vip_entities,
    update_entity,
    delete_entity,
    # Entity relationships
    create_relationship,
    get_entity_relationships,
    # Entity notes
    add_entity_note,
    get_entity_notes,
    get_entity_context,
)

__all__ = [
    # Identity
    "get_core_identity",
    "get_identity_value",
    "update_identity_value",
    "get_boundaries",
    "check_boundary",
    "get_values",
    # Knowledge
    "get_workflows",
    "get_workflow",
    "update_workflow_execution",
    "create_workflow",
    "get_preferences",
    "get_preference",
    "set_preference",
    # State
    "get_context_window",
    "set_context_window",
    "clear_context_windows",
    "get_pending_actions",
    "create_pending_action",
    "approve_pending_action",
    "reject_pending_action",
    "execute_pending_action",
    "get_session_state",
    "set_session_state",
    "update_session_state",
    # Evolution
    "log_evolution",
    "get_evolution_proposals",
    "approve_evolution",
    "apply_evolution",
    "record_metric",
    "get_metrics",
    "record_performance_metric",
    "record_feedback",
    "get_unprocessed_feedback",
    "mark_feedback_processed",
    # Status
    "get_brain_status",
    "update_brain_status",
    "record_synthesis_time",
    "record_evolution_time",
    "record_notion_sync_time",
    "log_notion_sync",
    "update_notion_sync_status",
    "get_pending_notion_syncs",
    # Composite
    "get_full_brain_context",
    "get_session_brief",
    "store_daily_impression",
    "store_daily_impressions_batch",
    "get_recent_impressions",
    "get_todays_impressions",
    "get_recent_sessions",
    "get_recent_observations",
    "get_recent_patterns",
    "get_recent_synthesis",
    "get_continuous_state_context",
    "create_entity",
    "get_entity",
    "get_entity_by_name",
    "search_entities",
    "get_entities_by_type",
    "get_vip_entities",
    "update_entity",
    "delete_entity",
    "create_relationship",
    "get_entity_relationships",
    "add_entity_note",
    "get_entity_notes",
    "get_entity_context",
]
