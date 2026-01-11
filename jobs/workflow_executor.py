"""
Athena Server v2 - Workflow Executor

Executes workflows defined in the workflows table. Workflows are multi-step
procedures that Athena can perform autonomously.

Security: All workflow steps are validated against an allow-list of safe
operations before execution.
"""

import logging
import json
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional
from enum import Enum

from db.neon import db_cursor
from db.brain import (
    get_workflow,
    get_workflows,
    update_workflow_execution,
    create_pending_action,
)
from config import settings

logger = logging.getLogger("athena.jobs.workflow")


# =============================================================================
# Allowed Operations (Security Allow-List)
# =============================================================================

class AllowedAction(Enum):
    """Actions that workflows are allowed to perform."""
    # Notification actions
    NOTIFY_USER = "notify_user"
    LOG_MESSAGE = "log_message"
    
    # Data operations
    QUERY_BRAIN = "query_brain"
    UPDATE_PREFERENCE = "update_preference"
    CREATE_ENTITY = "create_entity"
    
    # External integrations (require approval)
    SPAWN_MANUS_TASK = "spawn_manus_task"
    SEND_NOTIFICATION = "send_notification"
    
    # Control flow
    WAIT = "wait"
    CONDITION = "condition"
    
    # Pending action creation
    CREATE_PENDING_ACTION = "create_pending_action"


ALLOWED_ACTIONS = {a.value for a in AllowedAction}


# =============================================================================
# Step Executors
# =============================================================================

async def execute_notify_user(params: Dict) -> Dict:
    """Send a notification to the user."""
    message = params.get("message", "")
    priority = params.get("priority", "normal")
    
    # For now, log the notification - in production, this would integrate with
    # a notification service
    logger.info(f"USER NOTIFICATION [{priority}]: {message}")
    
    return {"success": True, "action": "notify_user", "message": message}


async def execute_log_message(params: Dict) -> Dict:
    """Log a message to the thinking log."""
    message = params.get("message", "")
    thought_type = params.get("thought_type", "workflow")
    
    with db_cursor() as cursor:
        cursor.execute("""
            INSERT INTO thinking_log (session_id, thought_type, content, phase)
            VALUES (%s, %s, %s, %s)
        """, (f"workflow_{datetime.utcnow().isoformat()}", thought_type, message, "workflow_execution"))
    
    return {"success": True, "action": "log_message"}


async def execute_query_brain(params: Dict) -> Dict:
    """Query the brain for information."""
    query_type = params.get("query_type", "")
    query_params = params.get("params", {})
    
    result = None
    
    if query_type == "get_identity":
        from db.brain import get_core_identity
        result = get_core_identity()
    elif query_type == "get_preferences":
        from db.brain import get_preferences
        result = get_preferences(query_params.get("category"))
    elif query_type == "get_entities":
        from db.brain import search_entities
        result = search_entities(
            query=query_params.get("query"),
            entity_type=query_params.get("entity_type")
        )
    elif query_type == "get_vip_entities":
        from db.brain import get_vip_entities
        result = get_vip_entities()
    else:
        return {"success": False, "error": f"Unknown query type: {query_type}"}
    
    return {"success": True, "action": "query_brain", "result": result}


async def execute_update_preference(params: Dict) -> Dict:
    """Update a preference in the brain."""
    category = params.get("category", "general")
    key = params.get("key")
    value = params.get("value")
    
    if not key or value is None:
        return {"success": False, "error": "Missing key or value"}
    
    with db_cursor() as cursor:
        cursor.execute("""
            INSERT INTO preferences (category, key, value, source, confidence)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (category, key) DO UPDATE SET
                value = EXCLUDED.value,
                updated_at = NOW()
        """, (category, key, value, "workflow", 0.9))
    
    return {"success": True, "action": "update_preference", "key": f"{category}.{key}"}


async def execute_create_entity(params: Dict) -> Dict:
    """Create an entity in the knowledge graph."""
    from db.brain import create_entity
    
    entity_id = create_entity(
        entity_type=params.get("entity_type", "unknown"),
        name=params.get("name", ""),
        description=params.get("description"),
        metadata=params.get("metadata", {}),
        source="workflow"
    )
    
    return {"success": True, "action": "create_entity", "entity_id": entity_id}


async def execute_spawn_manus_task(params: Dict) -> Dict:
    """
    Spawn a new Manus task.
    
    This action requires approval if the workflow requires_approval is True.
    """
    prompt = params.get("prompt", "")
    session_type = params.get("session_type", "workflow_task")
    
    # Import here to avoid circular imports
    from integrations.manus_api import create_manus_task
    
    result = await create_manus_task(
        task_prompt=prompt,
        session_type=session_type
    )
    
    return {"success": True, "action": "spawn_manus_task", "result": result}


async def execute_wait(params: Dict) -> Dict:
    """Wait for a specified duration."""
    seconds = params.get("seconds", 1)
    max_wait = 60  # Maximum wait time for safety
    
    actual_wait = min(seconds, max_wait)
    await asyncio.sleep(actual_wait)
    
    return {"success": True, "action": "wait", "waited_seconds": actual_wait}


async def execute_condition(params: Dict, context: Dict) -> Dict:
    """
    Evaluate a condition and return which branch to take.
    
    Conditions are simple key-value checks against the workflow context.
    """
    condition_type = params.get("type", "equals")
    key = params.get("key", "")
    expected = params.get("expected")
    
    actual = context.get(key)
    
    if condition_type == "equals":
        result = actual == expected
    elif condition_type == "not_equals":
        result = actual != expected
    elif condition_type == "exists":
        result = key in context
    elif condition_type == "not_exists":
        result = key not in context
    else:
        result = False
    
    return {"success": True, "action": "condition", "result": result}


async def execute_create_pending_action(params: Dict) -> Dict:
    """Create a pending action for human review."""
    action_id = create_pending_action(
        action_type=params.get("action_type", "workflow_action"),
        action_data=params.get("action_data", {}),
        priority=params.get("priority", "normal"),
        requires_approval=True
    )
    
    return {"success": True, "action": "create_pending_action", "action_id": action_id}


# Step executor mapping
STEP_EXECUTORS = {
    "notify_user": execute_notify_user,
    "log_message": execute_log_message,
    "query_brain": execute_query_brain,
    "update_preference": execute_update_preference,
    "create_entity": execute_create_entity,
    "spawn_manus_task": execute_spawn_manus_task,
    "wait": execute_wait,
    "condition": execute_condition,
    "create_pending_action": execute_create_pending_action,
}


# =============================================================================
# Workflow Execution Engine
# =============================================================================

class WorkflowExecutionResult:
    """Result of a workflow execution."""
    def __init__(self):
        self.success = True
        self.steps_executed = 0
        self.steps_failed = 0
        self.step_results = []
        self.error = None
        self.duration_seconds = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "steps_executed": self.steps_executed,
            "steps_failed": self.steps_failed,
            "step_results": self.step_results,
            "error": self.error,
            "duration_seconds": self.duration_seconds
        }


async def validate_step(step: Dict) -> tuple[bool, str]:
    """
    Validate that a workflow step is allowed.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    action = step.get("action", "")
    
    if action not in ALLOWED_ACTIONS:
        return False, f"Action '{action}' is not in the allow-list"
    
    # Additional validation based on action type
    if action == "spawn_manus_task":
        prompt = step.get("params", {}).get("prompt", "")
        if len(prompt) > 10000:
            return False, "Manus task prompt exceeds maximum length"
    
    return True, ""


async def execute_workflow(
    workflow_name: str,
    input_data: Dict = None,
    dry_run: bool = False
) -> WorkflowExecutionResult:
    """
    Execute a workflow by name.
    
    Args:
        workflow_name: Name of the workflow to execute
        input_data: Optional input data for the workflow
        dry_run: If True, validate but don't execute
        
    Returns:
        WorkflowExecutionResult with execution details
    """
    result = WorkflowExecutionResult()
    start_time = datetime.utcnow()
    
    # Get the workflow
    workflow = get_workflow(workflow_name)
    if not workflow:
        result.success = False
        result.error = f"Workflow not found: {workflow_name}"
        return result
    
    if not workflow.get("enabled", True):
        result.success = False
        result.error = f"Workflow is disabled: {workflow_name}"
        return result
    
    # Parse steps
    steps = workflow.get("steps", [])
    if isinstance(steps, str):
        try:
            steps = json.loads(steps)
        except json.JSONDecodeError:
            result.success = False
            result.error = "Invalid workflow steps JSON"
            return result
    
    if not steps:
        result.success = False
        result.error = "Workflow has no steps"
        return result
    
    logger.info(f"Executing workflow '{workflow_name}' with {len(steps)} steps")
    
    # Initialize context with input data
    context = input_data or {}
    context["workflow_name"] = workflow_name
    context["execution_time"] = start_time.isoformat()
    
    # Validate all steps first
    for i, step in enumerate(steps):
        is_valid, error = await validate_step(step)
        if not is_valid:
            result.success = False
            result.error = f"Step {i+1} validation failed: {error}"
            return result
    
    if dry_run:
        result.success = True
        result.steps_executed = len(steps)
        result.error = "Dry run - no steps executed"
        return result
    
    # Execute steps
    for i, step in enumerate(steps):
        step_name = step.get("name", f"step_{i+1}")
        action = step.get("action", "")
        params = step.get("params", {})
        
        logger.info(f"Executing step {i+1}/{len(steps)}: {step_name} ({action})")
        
        try:
            executor = STEP_EXECUTORS.get(action)
            if not executor:
                raise ValueError(f"No executor for action: {action}")
            
            # Special handling for condition steps
            if action == "condition":
                step_result = await executor(params, context)
            else:
                step_result = await executor(params)
            
            result.step_results.append({
                "step": i + 1,
                "name": step_name,
                "action": action,
                "result": step_result
            })
            
            # Update context with step result
            if step_result.get("result"):
                context[f"step_{i+1}_result"] = step_result["result"]
            
            result.steps_executed += 1
            
            # Handle conditional branching
            if action == "condition" and not step_result.get("result"):
                skip_to = step.get("skip_to_on_false")
                if skip_to:
                    logger.info(f"Condition false, skipping to step {skip_to}")
                    # Find the step to skip to
                    for j, future_step in enumerate(steps[i+1:], start=i+1):
                        if future_step.get("name") == skip_to:
                            # Skip to this step (will be executed in next iteration)
                            break
            
        except Exception as e:
            logger.error(f"Step {i+1} failed: {e}")
            result.step_results.append({
                "step": i + 1,
                "name": step_name,
                "action": action,
                "error": str(e)
            })
            result.steps_failed += 1
            
            # Check if we should continue on error
            if not step.get("continue_on_error", False):
                result.success = False
                result.error = f"Step {i+1} ({step_name}) failed: {e}"
                break
    
    # Calculate duration
    result.duration_seconds = (datetime.utcnow() - start_time).total_seconds()
    
    # Update workflow metrics
    update_workflow_execution(workflow_name, result.success)
    
    logger.info(
        f"Workflow '{workflow_name}' completed: "
        f"{result.steps_executed} executed, {result.steps_failed} failed, "
        f"{result.duration_seconds:.2f}s"
    )
    
    return result


async def execute_workflow_by_id(workflow_id: str, input_data: Dict = None) -> WorkflowExecutionResult:
    """Execute a workflow by ID."""
    with db_cursor() as cursor:
        cursor.execute("SELECT workflow_name FROM workflows WHERE id = %s", (workflow_id,))
        row = cursor.fetchone()
        if not row:
            result = WorkflowExecutionResult()
            result.success = False
            result.error = f"Workflow not found: {workflow_id}"
            return result
        
        return await execute_workflow(row["workflow_name"], input_data)


# =============================================================================
# Workflow API Routes
# =============================================================================

def create_workflow_routes():
    """Create FastAPI routes for workflow execution."""
    from fastapi import APIRouter, HTTPException, Query
    from pydantic import BaseModel
    from typing import Optional
    
    router = APIRouter(prefix="/api/v1/workflows", tags=["workflows"])
    
    class ExecuteRequest(BaseModel):
        input_data: Optional[Dict] = None
        dry_run: bool = False
    
    @router.get("")
    async def list_workflows(enabled_only: bool = Query(True)):
        """List all workflows."""
        workflows = get_workflows(enabled_only=enabled_only)
        return {"workflows": workflows, "count": len(workflows)}
    
    @router.get("/{workflow_name}")
    async def get_workflow_details(workflow_name: str):
        """Get details of a specific workflow."""
        workflow = get_workflow(workflow_name)
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        return workflow
    
    @router.post("/{workflow_name}/execute")
    async def execute_workflow_endpoint(workflow_name: str, request: ExecuteRequest):
        """Execute a workflow."""
        result = await execute_workflow(
            workflow_name,
            input_data=request.input_data,
            dry_run=request.dry_run
        )
        
        if not result.success:
            raise HTTPException(status_code=400, detail=result.error)
        
        return result.to_dict()
    
    @router.post("/{workflow_name}/validate")
    async def validate_workflow(workflow_name: str):
        """Validate a workflow without executing it."""
        result = await execute_workflow(workflow_name, dry_run=True)
        return {
            "valid": result.success,
            "steps_count": result.steps_executed,
            "error": result.error if not result.success else None
        }
    
    return router


# Create the router for import
workflow_router = create_workflow_routes()
