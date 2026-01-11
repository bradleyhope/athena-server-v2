"""
Athena Server v2 - Hourly Broadcast Job
Sends detailed thought transmissions every hour to:
1. The active Manus session (Workspace & Agenda)
2. The Athena Broadcasts Notion database
"""

import asyncio
import logging
import json
import httpx
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from config import settings
from db.neon import db_cursor, get_active_session
from db.brain import (
    get_brain_status, get_continuous_state_context,
    get_recent_observations, get_recent_patterns
)

logger = logging.getLogger("athena.jobs.hourly_broadcast")

# Athena Broadcasts database ID
BROADCASTS_DATABASE_ID = "70b8cb6eff9845d98492ce16c4e2e9aa"


async def get_active_workspace_session() -> Optional[Dict[str, Any]]:
    """Get the currently active Workspace & Agenda session."""
    try:
        session = get_active_session("workspace_agenda")
        if session:
            return {
                "task_id": session.get("manus_task_id"),
                "task_url": session.get("manus_task_url"),
                "session_date": session.get("session_date")
            }
        return None
    except Exception as e:
        logger.error(f"Failed to get active workspace session: {e}")
        return None


async def generate_thought_burst() -> Dict[str, Any]:
    """
    Generate a detailed thought burst based on current state.
    This is Athena's hourly transmission of her thinking.
    """
    now = datetime.utcnow()
    hour = now.hour
    
    # Get brain context
    try:
        brain_status = get_brain_status()
        continuous_state = get_continuous_state_context()
    except Exception as e:
        logger.error(f"Failed to get brain context: {e}")
        brain_status = {}
        continuous_state = {}
    
    # Get recent observations (last hour)
    recent_observations = continuous_state.get("recent_observations", [])[:5]
    recent_patterns = continuous_state.get("recent_patterns", [])[:3]
    pending_actions = continuous_state.get("pending_actions", [])[:3]
    
    # Determine thought type based on what's happening
    thought_type = "Thought"
    priority = "Medium"
    
    # Check for alerts
    if pending_actions:
        high_priority = [a for a in pending_actions if a.get("priority") == "high"]
        if high_priority:
            thought_type = "Alert"
            priority = "High"
    
    # Check for insights
    if recent_patterns:
        high_confidence = [p for p in recent_patterns if p.get("confidence", 0) > 0.8]
        if high_confidence:
            thought_type = "Insight"
            priority = "High"
    
    # Build the thought content
    thought_lines = []
    
    # Time context
    if 5 <= hour < 12:
        time_context = "Morning analysis"
    elif 12 <= hour < 17:
        time_context = "Afternoon monitoring"
    elif 17 <= hour < 21:
        time_context = "Evening review"
    else:
        time_context = "Overnight watch"
    
    thought_lines.append(f"**{time_context}** - {now.strftime('%H:%M UTC')}")
    thought_lines.append("")
    
    # Recent observations
    if recent_observations:
        thought_lines.append("**Recent Observations:**")
        for obs in recent_observations[:3]:
            thought_lines.append(f"- [{obs.get('category', 'general').upper()}] {obs.get('content', '')[:100]}")
        thought_lines.append("")
    
    # Patterns detected
    if recent_patterns:
        thought_lines.append("**Patterns Detected:**")
        for pat in recent_patterns[:2]:
            conf = pat.get('confidence', 0)
            thought_lines.append(f"- {pat.get('description', '')[:80]}... ({conf:.0%} confidence)")
        thought_lines.append("")
    
    # Pending actions
    if pending_actions:
        thought_lines.append("**Pending Actions (Awaiting Your Review):**")
        for action in pending_actions[:3]:
            thought_lines.append(f"- [{action.get('priority', 'medium').upper()}] {action.get('description', '')[:80]}")
        thought_lines.append("")
    
    # Learning stats
    learning_stats = continuous_state.get("learning_stats", {})
    if learning_stats:
        obs_count = learning_stats.get("observations_this_week", 0)
        pattern_count = learning_stats.get("total_patterns_detected", 0)
        thought_lines.append(f"**This Week:** {obs_count} observations, {pattern_count} patterns")
    
    # Build summary title
    if thought_type == "Alert":
        title = f"⚠️ {len(pending_actions)} actions need your attention"
    elif thought_type == "Insight":
        title = f"💡 New pattern detected: {recent_patterns[0].get('type', 'unknown') if recent_patterns else 'unknown'}"
    else:
        title = f"🧠 {time_context}: {len(recent_observations)} observations"
    
    return {
        "title": title,
        "content": "\n".join(thought_lines),
        "type": thought_type,
        "priority": priority,
        "confidence": 0.8,
        "session_id": f"hourly_{now.strftime('%Y%m%d_%H')}",
        "timestamp": now.isoformat()
    }


async def send_to_manus_session(session: Dict[str, Any], thought: Dict[str, Any]) -> bool:
    """
    Send the thought burst to the active Manus session.
    Uses the Manus API to send a message to an existing task.
    """
    task_id = session.get("task_id")
    if not task_id:
        logger.warning("No task_id in active session")
        return False
    
    # Format the message for Manus
    message = f"""
---
## 📡 ATHENA BROADCAST - {thought['timestamp'][:16]}

{thought['content']}

---
*This is an automated hourly transmission from Athena's thinking process.*
"""
    
    try:
        async with httpx.AsyncClient() as client:
            # Send message to the Manus task
            response = await client.post(
                f"{settings.MANUS_API_BASE}/tasks/{task_id}/messages",
                headers={
                    "Authorization": f"Bearer {settings.MANUS_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={"content": message},
                timeout=30.0
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"Sent thought burst to Manus session {task_id}")
                return True
            else:
                logger.warning(f"Failed to send to Manus: {response.status_code} - {response.text}")
                return False
    except Exception as e:
        logger.error(f"Error sending to Manus session: {e}")
        return False


async def send_to_notion(thought: Dict[str, Any]) -> bool:
    """
    Send the thought burst to the Athena Broadcasts Notion database.
    """
    notion_api_key = settings.NOTION_API_KEY
    if not notion_api_key:
        logger.warning("NOTION_API_KEY not configured")
        return False
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.notion.com/v1/pages",
                headers={
                    "Authorization": f"Bearer {notion_api_key}",
                    "Content-Type": "application/json",
                    "Notion-Version": "2022-06-28"
                },
                json={
                    "parent": {"database_id": BROADCASTS_DATABASE_ID},
                    "properties": {
                        "Name": {
                            "title": [{"text": {"content": thought["title"][:100]}}]
                        },
                        "Type": {
                            "select": {"name": thought["type"]}
                        },
                        "Priority": {
                            "select": {"name": thought["priority"]}
                        },
                        "Status": {
                            "select": {"name": "New"}
                        },
                        "Confidence": {
                            "number": thought["confidence"]
                        },
                        "Session ID": {
                            "rich_text": [{"text": {"content": thought["session_id"]}}]
                        },
                        "Timestamp": {
                            "date": {"start": thought["timestamp"]}
                        }
                    },
                    "children": [
                        {
                            "object": "block",
                            "type": "paragraph",
                            "paragraph": {
                                "rich_text": [{"type": "text", "text": {"content": thought["content"][:2000]}}]
                            }
                        }
                    ]
                },
                timeout=30.0
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"Sent thought burst to Notion database")
                return True
            else:
                logger.warning(f"Failed to send to Notion: {response.status_code} - {response.text}")
                return False
    except Exception as e:
        logger.error(f"Error sending to Notion: {e}")
        return False


async def run_hourly_broadcast():
    """
    Main entry point for the hourly broadcast job.
    Generates a thought burst and sends it to both Manus and Notion.
    """
    logger.info("Starting hourly broadcast")
    
    # Generate the thought burst
    thought = await generate_thought_burst()
    logger.info(f"Generated thought burst: {thought['title']}")
    
    results = {
        "thought": thought,
        "manus_sent": False,
        "notion_sent": False
    }
    
    # Get active workspace session
    active_session = await get_active_workspace_session()
    
    # Send to Manus if there's an active session
    if active_session:
        results["manus_sent"] = await send_to_manus_session(active_session, thought)
    else:
        logger.info("No active workspace session - skipping Manus broadcast")
    
    # Send to Notion
    results["notion_sent"] = await send_to_notion(thought)
    
    logger.info(f"Hourly broadcast complete: Manus={results['manus_sent']}, Notion={results['notion_sent']}")
    return results
