"""
Athena Server v2 - Hourly Broadcast Job
Sends detailed thought transmissions every hour by:
1. Spawning a NEW Manus task with the broadcast (only when actionable)
2. Logging to the Athena Broadcasts Notion database (always)

Active hours: 5:30 AM - 10:30 PM London time
Manus tasks: Only spawned when there's something actionable (alerts, urgent items, new patterns)
"""

import asyncio
import logging
import json
import httpx
from datetime import datetime, time
from typing import Dict, Any, Optional, List
import pytz

from config import settings, MANUS_CONNECTORS
from db.neon import db_cursor, get_active_session, store_broadcast, ensure_broadcasts_table
from db.brain import (
    get_brain_status, get_continuous_state_context,
    get_recent_patterns
)
from db.brain.composite import get_recent_observations
from integrations.manus_api import create_manus_task

logger = logging.getLogger("athena.jobs.hourly_broadcast")

# Build broadcast time window from config
BROADCAST_START = time(settings.BROADCAST_START_HOUR, settings.BROADCAST_START_MINUTE)
BROADCAST_END = time(settings.BROADCAST_END_HOUR, settings.BROADCAST_END_MINUTE)


def is_active_hours() -> bool:
    """Check if we're within active broadcast hours (configurable via settings)."""
    london_tz = pytz.timezone('Europe/London')
    now = datetime.now(london_tz).time()
    return BROADCAST_START <= now <= BROADCAST_END


def is_actionable(thought: Dict[str, Any], observations: List[Dict]) -> tuple[bool, str]:
    """
    Determine if a broadcast is worth spawning a Manus task for.
    
    Returns:
        (is_actionable, reason)
    """
    # Always actionable: Alerts (high priority pending actions)
    if thought.get("type") == "Alert":
        return True, "High priority actions pending"
    
    # Always actionable: New high-confidence patterns
    if thought.get("type") == "Insight":
        return True, "New pattern detected"
    
    # Check for urgent emails (keywords in observations)
    urgent_keywords = ["urgent", "asap", "deadline", "overdue", "action required", "respond", "waiting for"]
    for obs in observations:
        content = obs.get("content", "").lower()
        for keyword in urgent_keywords:
            if keyword in content:
                return True, f"Urgent content detected: '{keyword}'"
    
    # Check for upcoming meetings (within 2 hours)
    for obs in observations:
        if obs.get("category") == "meeting":
            # Could add time parsing here to check if meeting is soon
            pass
    
    # Check for high volume of observations (unusual activity)
    if len(observations) >= 15:
        return True, f"High activity: {len(observations)} observations in last hour"
    
    # Not actionable - just routine monitoring
    return False, "Routine monitoring - no urgent items"


async def generate_thought_burst() -> tuple[Dict[str, Any], List[Dict]]:
    """
    Generate a detailed thought burst based on current state.
    Returns both the thought and the raw observations for actionability check.
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
    
    # Get recent observations from the LAST HOUR
    try:
        recent_observations = get_recent_observations(limit=20, hours=1)
    except Exception as e:
        logger.error(f"Failed to get hourly observations: {e}")
        recent_observations = []
    
    # Get patterns and pending actions from continuous state
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
    
    # Categorize observations for smarter display
    emails = [o for o in recent_observations if o.get("source_type") == "gmail"]
    meetings = [o for o in recent_observations if o.get("source_type") == "calendar"]
    other = [o for o in recent_observations if o.get("source_type") not in ["gmail", "calendar"]]
    
    # Show emails with more context
    if emails:
        thought_lines.append(f"**📧 Emails ({len(emails)}):**")
        for email in emails[:5]:
            content = email.get("content", "")[:80]
            # Try to extract subject/sender if available
            thought_lines.append(f"- {content}")
        if len(emails) > 5:
            thought_lines.append(f"  ... and {len(emails) - 5} more")
        thought_lines.append("")
    
    # Show meetings
    if meetings:
        thought_lines.append(f"**📅 Calendar ({len(meetings)}):**")
        for meeting in meetings[:3]:
            thought_lines.append(f"- {meeting.get('content', '')[:80]}")
        thought_lines.append("")
    
    # Patterns detected
    if recent_patterns:
        thought_lines.append("**🔍 Patterns Detected:**")
        for pat in recent_patterns[:2]:
            conf = pat.get('confidence', 0)
            thought_lines.append(f"- {pat.get('description', '')[:80]}... ({conf:.0%} confidence)")
        thought_lines.append("")
    
    # Pending actions - this is the most important part
    if pending_actions:
        thought_lines.append("**⚠️ Actions Needed:**")
        for action in pending_actions[:3]:
            thought_lines.append(f"- [{action.get('priority', 'medium').upper()}] {action.get('description', '')[:80]}")
        thought_lines.append("")
    
    # Build summary title
    if thought_type == "Alert":
        title = f"⚠️ {len(pending_actions)} actions need your attention"
    elif thought_type == "Insight":
        title = f"💡 New pattern detected: {recent_patterns[0].get('pattern_name', 'unknown') if recent_patterns else 'unknown'}"
    else:
        obs_count = len(recent_observations)
        if obs_count == 0:
            title = f"🧠 {time_context}: All quiet"
        else:
            # More informative title
            parts = []
            if emails:
                parts.append(f"{len(emails)} emails")
            if meetings:
                parts.append(f"{len(meetings)} calendar")
            title = f"🧠 {time_context}: {', '.join(parts) if parts else f'{obs_count} observations'}"
    
    thought = {
        "title": title,
        "content": "\n".join(thought_lines),
        "type": thought_type,
        "priority": priority,
        "confidence": 0.8,
        "session_id": f"hourly_{now.strftime('%Y%m%d_%H')}",
        "timestamp": now.isoformat()
    }
    
    return thought, recent_observations


async def spawn_broadcast_task(thought: Dict[str, Any], reason: str) -> Optional[str]:
    """
    Spawn a NEW Manus task to deliver the broadcast.
    This is how broadcasts reach Bradley - as new tasks in his Manus feed.
    """
    london_tz = pytz.timezone('Europe/London')
    now = datetime.now(london_tz)
    
    # Build the lean broadcast prompt - purely task-focused, no identity claims
    prompt = f"""## 📡 Athena Broadcast

**Time:** {now.strftime('%A, %B %d, %Y at %H:%M')} London time
**Type:** {thought['type']} | **Priority:** {thought['priority']}
**Why you're seeing this:** {reason}

---

{thought['content']}

---

## Quick Actions

- **Acknowledge**: Say "noted" to dismiss
- **Feedback**: Tell me if this was useful or not
- **Action**: Ask me to help with any item above

This is a quick check-in. I'll only interrupt when something needs attention."""

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
                    "parent": {"database_id": settings.BROADCASTS_DATABASE_ID},
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
                        "Session ID": {
                            "rich_text": [{"text": {"content": thought["session_id"]}}]
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
            
            if response.status_code == 200:
                logger.info("Sent thought burst to Notion")
                return True
            else:
                logger.error(f"Failed to send to Notion: {response.status_code} - {response.text[:200]}")
                return False
                
    except Exception as e:
        logger.error(f"Error sending to Notion: {e}")
        return False


async def run_hourly_broadcast():
    """
    Main entry point for the hourly broadcast job.
    
    - Always generates a thought burst
    - Always logs to Notion and database
    - Only spawns Manus task when there's something ACTIONABLE
    """
    logger.info("Starting hourly broadcast")
    
    # Generate the thought burst
    thought, observations = await generate_thought_burst()
    logger.info(f"Generated thought burst: {thought['title']}")
    
    # Check if this broadcast is worth interrupting Bradley for
    actionable, reason = is_actionable(thought, observations)
    
    results = {
        "thought": thought,
        "manus_task_id": None,
        "notion_sent": False,
        "is_active_hours": is_active_hours(),
        "is_actionable": actionable,
        "actionable_reason": reason
    }
    
    # Always send to Notion (for record keeping)
    results["notion_sent"] = await send_to_notion(thought)
    
    # Also store in database for ATHENA THINKING to fetch
    try:
        thought['notion_synced'] = results['notion_sent']
        thought['actionable'] = actionable
        thought['actionable_reason'] = reason
        broadcast_id = store_broadcast(thought)
        results['broadcast_id'] = broadcast_id
        logger.info(f"Stored broadcast in database: ID={broadcast_id}")
    except Exception as e:
        logger.error(f"Failed to store broadcast in database: {e}")
        results['broadcast_id'] = None
    
    # Only spawn Manus task if:
    # 1. Within active hours (5:30 AM - 10:30 PM London)
    # 2. Content is actionable (alerts, urgent items, new patterns)
    if is_active_hours() and actionable:
        logger.info(f"Spawning Manus task - reason: {reason}")
        results["manus_task_id"] = await spawn_broadcast_task(thought, reason)
    elif is_active_hours():
        logger.info(f"Skipping Manus task - not actionable: {reason}")
    else:
        logger.info("Outside active hours - skipping Manus task")
    
    logger.info(f"Hourly broadcast complete: Notion={results['notion_sent']}, Actionable={actionable}, ManusTask={results['manus_task_id']}")
    return results
