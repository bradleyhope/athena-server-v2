"""
Athena Server v2 - Hourly Broadcast Job
Sends detailed thought transmissions every hour by:
1. Spawning a NEW Manus task with the broadcast (during active hours only)
2. Logging to the Athena Broadcasts Notion database (always)

Active hours: 5:30 AM - 10:30 PM London time
Outside active hours: Bursts are generated and stored in Notion but not broadcast to Manus
"""

import asyncio
import logging
import json
import httpx
from datetime import datetime, time
from typing import Dict, Any, Optional, List
import pytz

from config import settings, MANUS_CONNECTORS
from db.neon import db_cursor, get_active_session
from db.brain import (
    get_brain_status, get_continuous_state_context,
    get_recent_observations, get_recent_patterns
)
from integrations.manus_api import create_manus_task

logger = logging.getLogger("athena.jobs.hourly_broadcast")

# Athena Broadcasts database ID
BROADCASTS_DATABASE_ID = "70b8cb6eff9845d98492ce16c4e2e9aa"

# Active broadcast hours (London time)
BROADCAST_START = time(5, 30)   # 5:30 AM
BROADCAST_END = time(22, 30)    # 10:30 PM


def is_active_hours() -> bool:
    """Check if we're within active broadcast hours (5:30 AM - 10:30 PM London)."""
    london_tz = pytz.timezone('Europe/London')
    now = datetime.now(london_tz).time()
    return BROADCAST_START <= now <= BROADCAST_END


async def generate_thought_burst() -> Dict[str, Any]:
    """
    Generate a detailed thought burst based on current state.
    This is Athena's hourly transmission of her thinking.
    """
    london_tz = pytz.timezone('Europe/London')
    now = datetime.now(london_tz)
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
    
    thought_lines.append(f"**{time_context}** - {now.strftime('%H:%M')} London time")
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


async def spawn_broadcast_task(thought: Dict[str, Any]) -> Optional[str]:
    """
    Spawn a NEW Manus task to deliver the broadcast.
    This is how broadcasts reach Bradley - as new tasks in his Manus feed.
    """
    london_tz = pytz.timezone('Europe/London')
    now = datetime.now(london_tz)
    
    # Build the broadcast prompt
    prompt = f"""You are Athena, Bradley Hope's cognitive extension. This is an HOURLY BROADCAST from your autonomous thinking process.

## 📡 ATHENA BROADCAST
**Time:** {now.strftime('%A, %B %d, %Y at %H:%M')} London time
**Type:** {thought['type']}
**Priority:** {thought['priority']}

---

{thought['content']}

---

## Your Task

1. **Present this broadcast to Bradley** - Display the above information clearly
2. **Assess the signal** - Is this useful? Accurate? Actionable?
3. **Provide your evaluation** - Brief assessment of the broadcast quality
4. **Ask Bradley** - Does he have any feedback on this broadcast?

If Bradley indicates this broadcast is off-base or unhelpful:
- Use POST https://athena-server-0dce.onrender.com/api/brain/feedback to submit a correction
- Header: Authorization: Bearer athena_api_key_2024
- Body: {{"feedback_type": "correction", "original_content": "...", "correction": "...", "severity": "minor|moderate|major"}}

This helps Athena learn and improve her thinking.

Be concise. This is a quick check-in, not a full session."""

    try:
        result = await create_manus_task(
            prompt=prompt,
            connectors=MANUS_CONNECTORS
        )
        
        if result and result.get('id'):
            task_id = result['id']
            logger.info(f"Spawned broadcast task: {task_id}")
            return task_id
        else:
            logger.error("Failed to spawn broadcast task")
            return None
    except Exception as e:
        logger.error(f"Error spawning broadcast task: {e}")
        return None


async def send_to_notion(thought: Dict[str, Any]) -> bool:
    """
    Send the thought burst to the Athena Broadcasts Notion database.
    This happens regardless of active hours - all bursts are logged.
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
    
    - Always generates a thought burst
    - Always logs to Notion
    - Only spawns Manus task during active hours (5:30 AM - 10:30 PM London)
    """
    logger.info("Starting hourly broadcast")
    
    # Generate the thought burst
    thought = await generate_thought_burst()
    logger.info(f"Generated thought burst: {thought['title']}")
    
    results = {
        "thought": thought,
        "manus_task_id": None,
        "notion_sent": False,
        "is_active_hours": is_active_hours()
    }
    
    # Always send to Notion (for record keeping)
    results["notion_sent"] = await send_to_notion(thought)
    
    # Only spawn Manus task during active hours
    if is_active_hours():
        logger.info("Within active hours - spawning Manus broadcast task")
        results["manus_task_id"] = await spawn_broadcast_task(thought)
    else:
        logger.info("Outside active hours - skipping Manus broadcast (stored in Notion only)")
    
    logger.info(f"Hourly broadcast complete: Manus={results['manus_task_id']}, Notion={results['notion_sent']}, ActiveHours={results['is_active_hours']}")
    return results
