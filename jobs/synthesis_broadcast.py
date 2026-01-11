"""
Athena Server v2 - Synthesis Broadcast Job
Generates higher-level strategic insights twice daily (5:30 AM and 5:30 PM London time).

This is Tier 2 thinking - Athena reads ALL bursts from the period, combines with her
brain context, and generates meta-insights about what she's really seeing.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import pytz

from config import settings, MANUS_CONNECTORS
from db.neon import db_cursor
from db.brain import (
    get_brain_status, get_continuous_state_context,
    get_recent_observations, get_recent_patterns,
    get_pending_actions, get_evolution_proposals
)
from integrations.manus_api import create_manus_task

logger = logging.getLogger("athena.jobs.synthesis_broadcast")


async def get_recent_bursts(hours: int = 12) -> List[Dict[str, Any]]:
    """Get all thought bursts from the last N hours from the thinking_log table."""
    try:
        with db_cursor() as cur:
            cur.execute("""
                SELECT session_id, thought_type, content, confidence, metadata, created_at
                FROM thinking_log
                WHERE created_at > NOW() - INTERVAL '%s hours'
                ORDER BY created_at DESC
            """, (hours,))
            rows = cur.fetchall()
            return [
                {
                    "session_id": row["session_id"],
                    "type": row["thought_type"],
                    "content": row["content"],
                    "confidence": row["confidence"],
                    "metadata": row["metadata"],
                    "timestamp": row["created_at"].isoformat() if row["created_at"] else None
                }
                for row in rows
            ]
    except Exception as e:
        logger.error(f"Failed to get recent bursts: {e}")
        return []


async def generate_synthesis() -> Dict[str, Any]:
    """
    Generate a strategic synthesis by analyzing all recent bursts and brain context.
    This is Athena's higher-level thinking about her own thoughts.
    """
    london_tz = pytz.timezone('Europe/London')
    now = datetime.now(london_tz)
    hour = now.hour
    
    # Determine if this is morning or evening synthesis
    if hour < 12:
        synthesis_type = "Morning Synthesis"
        period = "overnight"
        hours_back = 12  # Look at overnight bursts
    else:
        synthesis_type = "Evening Synthesis"
        period = "today"
        hours_back = 12  # Look at day's bursts
    
    # Get recent bursts
    recent_bursts = await get_recent_bursts(hours_back)
    
    # Get brain context
    try:
        continuous_state = get_continuous_state_context()
        brain_status = get_brain_status()
    except Exception as e:
        logger.error(f"Failed to get brain context: {e}")
        continuous_state = {}
        brain_status = {}
    
    # Get patterns and observations
    recent_patterns = continuous_state.get("recent_patterns", [])
    recent_observations = continuous_state.get("recent_observations", [])
    pending_actions = continuous_state.get("pending_actions", [])
    evolution_proposals = get_evolution_proposals()
    
    # Analyze burst themes
    burst_types = {}
    for burst in recent_bursts:
        t = burst.get("type", "unknown")
        burst_types[t] = burst_types.get(t, 0) + 1
    
    # Build synthesis content
    synthesis_lines = []
    
    synthesis_lines.append(f"## {synthesis_type}")
    synthesis_lines.append(f"*Analyzing {period}'s activity ({now.strftime('%A, %B %d, %Y')})*")
    synthesis_lines.append("")
    
    # Overview
    synthesis_lines.append("### Overview")
    synthesis_lines.append(f"- **Bursts generated:** {len(recent_bursts)}")
    synthesis_lines.append(f"- **Observations collected:** {len(recent_observations)}")
    synthesis_lines.append(f"- **Patterns detected:** {len(recent_patterns)}")
    synthesis_lines.append(f"- **Pending actions:** {len(pending_actions)}")
    synthesis_lines.append("")
    
    # Burst breakdown
    if burst_types:
        synthesis_lines.append("### Burst Types")
        for btype, count in sorted(burst_types.items(), key=lambda x: -x[1]):
            synthesis_lines.append(f"- {btype}: {count}")
        synthesis_lines.append("")
    
    # Key themes (from patterns)
    if recent_patterns:
        synthesis_lines.append("### Key Themes Emerging")
        for i, pattern in enumerate(recent_patterns[:5], 1):
            conf = pattern.get("confidence", 0)
            synthesis_lines.append(f"{i}. **{pattern.get('type', 'Unknown')}** ({conf:.0%} confidence)")
            synthesis_lines.append(f"   {pattern.get('description', 'No description')[:150]}")
        synthesis_lines.append("")
    
    # High priority items
    high_priority = [a for a in pending_actions if a.get("priority") == "high"]
    if high_priority:
        synthesis_lines.append("### ⚠️ Requires Attention")
        for action in high_priority[:3]:
            synthesis_lines.append(f"- {action.get('description', 'No description')[:100]}")
        synthesis_lines.append("")
    
    # Evolution proposals
    pending_evolution = [e for e in evolution_proposals if e.get("status") == "pending"]
    if pending_evolution:
        synthesis_lines.append("### 🔄 Evolution Proposals")
        for evo in pending_evolution[:2]:
            synthesis_lines.append(f"- **{evo.get('proposal_type', 'Unknown')}:** {evo.get('description', '')[:100]}")
        synthesis_lines.append("")
    
    # Meta-insight (what I'm really seeing)
    synthesis_lines.append("### 💡 Meta-Insight")
    if len(recent_patterns) > 3:
        synthesis_lines.append("Multiple patterns are converging. There may be a larger theme worth exploring.")
    elif high_priority:
        synthesis_lines.append("Focus needed on high-priority items before they become urgent.")
    elif len(recent_bursts) < 3:
        synthesis_lines.append("Quiet period. Good time for strategic thinking or catching up on backlog.")
    else:
        synthesis_lines.append("Normal activity levels. Systems operating as expected.")
    synthesis_lines.append("")
    
    # Questions for Bradley
    synthesis_lines.append("### Questions for Bradley")
    synthesis_lines.append("1. Are there any patterns here that surprise you or seem off?")
    synthesis_lines.append("2. Should I adjust my focus for the next period?")
    synthesis_lines.append("3. Any feedback on the quality of my observations?")
    
    # Determine priority
    priority = "High" if high_priority else "Medium"
    
    return {
        "title": f"📊 {synthesis_type}: {len(recent_bursts)} bursts analyzed",
        "content": "\n".join(synthesis_lines),
        "type": "Synthesis",
        "priority": priority,
        "confidence": 0.9,
        "session_id": f"synthesis_{now.strftime('%Y%m%d_%H')}",
        "timestamp": now.isoformat(),
        "metadata": {
            "bursts_analyzed": len(recent_bursts),
            "patterns_found": len(recent_patterns),
            "pending_actions": len(pending_actions),
            "synthesis_type": synthesis_type
        }
    }


async def spawn_synthesis_task(synthesis: Dict[str, Any]) -> Optional[str]:
    """
    Spawn a Manus task to deliver the synthesis broadcast.
    """
    london_tz = pytz.timezone('Europe/London')
    now = datetime.now(london_tz)
    
    prompt = f"""You are Athena, Bradley Hope's cognitive extension. This is a SYNTHESIS BROADCAST - a strategic analysis of my recent thinking.

## 📊 ATHENA SYNTHESIS
**Time:** {now.strftime('%A, %B %d, %Y at %H:%M')} London time
**Type:** {synthesis['type']}
**Priority:** {synthesis['priority']}

---

{synthesis['content']}

---

## Your Task

1. **Present this synthesis to Bradley** - This is strategic-level insight, not tactical
2. **Highlight the most important findings** - What should Bradley focus on?
3. **Answer Bradley's questions** - Help him understand the patterns
4. **Collect feedback** - If anything is off, submit corrections to help me learn

If Bradley has feedback:
- Use POST https://athena-server-0dce.onrender.com/api/brain/feedback
- Header: Authorization: Bearer athena_api_key_2024
- Body: {{"feedback_type": "correction|praise|suggestion", "content": "...", "context": "synthesis"}}

This synthesis represents my higher-level thinking about my own thoughts. Help Bradley see the big picture."""

    try:
        result = await create_manus_task(
            prompt=prompt,
            connectors=MANUS_CONNECTORS
        )
        
        if result and result.get('id'):
            task_id = result['id']
            logger.info(f"Spawned synthesis task: {task_id}")
            return task_id
        else:
            logger.error("Failed to spawn synthesis task")
            return None
    except Exception as e:
        logger.error(f"Error spawning synthesis task: {e}")
        return None


async def log_synthesis_to_notion(synthesis: Dict[str, Any]) -> bool:
    """Log the synthesis to the Athena Broadcasts Notion database."""
    notion_api_key = settings.NOTION_API_KEY
    if not notion_api_key:
        logger.warning("NOTION_API_KEY not configured")
        return False
    
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.notion.com/v1/pages",
                headers={
                    "Authorization": f"Bearer {notion_api_key}",
                    "Content-Type": "application/json",
                    "Notion-Version": "2022-06-28"
                },
                json={
                    "parent": {"database_id": "70b8cb6eff9845d98492ce16c4e2e9aa"},
                    "properties": {
                        "Name": {
                            "title": [{"text": {"content": synthesis["title"][:100]}}]
                        },
                        "Type": {
                            "select": {"name": "Synthesis"}
                        },
                        "Priority": {
                            "select": {"name": synthesis["priority"]}
                        },
                        "Status": {
                            "select": {"name": "New"}
                        },
                        "Confidence": {
                            "number": synthesis["confidence"]
                        },
                        "Session ID": {
                            "rich_text": [{"text": {"content": synthesis["session_id"]}}]
                        },
                        "Timestamp": {
                            "date": {"start": synthesis["timestamp"]}
                        }
                    },
                    "children": [
                        {
                            "object": "block",
                            "type": "paragraph",
                            "paragraph": {
                                "rich_text": [{"type": "text", "text": {"content": synthesis["content"][:2000]}}]
                            }
                        }
                    ]
                },
                timeout=30.0
            )
            
            if response.status_code in [200, 201]:
                logger.info("Logged synthesis to Notion")
                return True
            else:
                logger.warning(f"Failed to log to Notion: {response.status_code}")
                return False
    except Exception as e:
        logger.error(f"Error logging to Notion: {e}")
        return False


async def run_synthesis_broadcast():
    """
    Main entry point for the synthesis broadcast job.
    Runs at 5:30 AM and 5:30 PM London time.
    """
    logger.info("Starting synthesis broadcast")
    
    # Generate the synthesis
    synthesis = await generate_synthesis()
    logger.info(f"Generated synthesis: {synthesis['title']}")
    
    results = {
        "synthesis": synthesis,
        "manus_task_id": None,
        "notion_logged": False
    }
    
    # Spawn Manus task
    results["manus_task_id"] = await spawn_synthesis_task(synthesis)
    
    # Log to Notion
    results["notion_logged"] = await log_synthesis_to_notion(synthesis)
    
    logger.info(f"Synthesis broadcast complete: Manus={results['manus_task_id']}, Notion={results['notion_logged']}")
    return results
