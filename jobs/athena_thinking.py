"""
Athena Server v2 - ATHENA THINKING Job
Hybrid approach: Server-side processing + Manus session for broadcast/reasoning.

This job:
1. Runs server-side data collection (Gmail, Calendar) using Athena's credentials
2. Stores observations in Neon
3. Spawns a Manus session to broadcast thinking and handle complex reasoning
4. Falls back to MCP connectors if server-side fails
"""

import logging
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from config import settings
from db.neon import db_cursor
from db.brain import (
    get_brain_status,
    get_pending_actions,
    get_evolution_proposals,
    update_session_state,
    store_daily_impressions_batch,
)
from integrations.gmail_client import gmail_client
from integrations.calendar_client import calendar_client
from integrations.manus_api import create_manus_task, rename_manus_task, MANUS_CONNECTORS
from jobs.task_verification import run_task_verification

logger = logging.getLogger("athena.jobs.thinking")


async def collect_server_side_data() -> Dict:
    """
    Collect data using Athena's own credentials (server-side).
    
    Returns:
        Dict with emails, events, and any errors
    """
    logger.info("Starting server-side data collection...")
    
    result = {
        "emails": [],
        "events": [],
        "errors": [],
        "success": True
    }
    
    # Collect emails
    try:
        emails = await gmail_client.get_unread_emails(hours=24, max_results=50)
        result["emails"] = emails
        logger.info(f"Collected {len(emails)} unread emails")
    except Exception as e:
        logger.error(f"Failed to collect emails: {e}")
        result["errors"].append(f"Gmail: {str(e)}")
    
    # Collect calendar events
    try:
        events = await calendar_client.get_upcoming_events(hours=48)
        result["events"] = events
        logger.info(f"Collected {len(events)} upcoming events")
    except Exception as e:
        logger.error(f"Failed to collect calendar events: {e}")
        result["errors"].append(f"Calendar: {str(e)}")
    
    # Mark as failed if both failed
    if not result["emails"] and not result["events"] and result["errors"]:
        result["success"] = False
    
    return result


def store_observations(data: Dict) -> int:
    """
    Store collected data as observations in Neon.
    
    Returns:
        Number of observations stored
    """
    logger.info("Storing observations in Neon...")
    count = 0
    
    with db_cursor() as cursor:
        # Store email observations
        for email in data.get("emails", []):
            try:
                cursor.execute("""
                    INSERT INTO observations (source, observation_type, content, metadata, created_at)
                    VALUES (%s, %s, %s, %s, NOW())
                """, (
                    "gmail",
                    "email",
                    email.get("snippet", "")[:500],
                    json.dumps({
                        "id": email.get("id"),
                        "subject": email.get("subject"),
                        "from": email.get("from"),
                        "date": email.get("date"),
                        "labels": email.get("labels", [])
                    })
                ))
                count += 1
            except Exception as e:
                logger.warning(f"Failed to store email observation: {e}")
        
        # Store calendar observations
        for event in data.get("events", []):
            try:
                cursor.execute("""
                    INSERT INTO observations (source, observation_type, content, metadata, created_at)
                    VALUES (%s, %s, %s, %s, NOW())
                """, (
                    "calendar",
                    "event",
                    event.get("summary", "")[:500],
                    json.dumps({
                        "id": event.get("id"),
                        "start_time": event.get("start_time"),
                        "end_time": event.get("end_time"),
                        "location": event.get("location"),
                        "attendees": event.get("attendees", [])
                    })
                ))
                count += 1
            except Exception as e:
                logger.warning(f"Failed to store calendar observation: {e}")
    
    logger.info(f"Stored {count} observations")
    return count


async def spawn_thinking_session(
    data: Dict,
    use_mcp_fallback: bool = False,
    verification_result: Dict = None
) -> Optional[Dict]:
    """
    Spawn a Manus session for ATHENA THINKING broadcast.
    
    Args:
        data: Collected data from server-side processing
        use_mcp_fallback: If True, enable MCP connectors as fallback
        
    Returns:
        Task result dict or None
    """
    today = datetime.now().strftime("%B %d, %Y")
    session_name = f"ATHENA THINKING {today}"
    
    # Build the task prompt with collected data
    email_summary = f"{len(data.get('emails', []))} unread emails"
    event_summary = f"{len(data.get('events', []))} upcoming events"
    
    # Format key emails for the prompt
    email_highlights = []
    for email in data.get("emails", [])[:10]:  # Top 10
        email_highlights.append(f"- From: {email.get('from', 'unknown')[:50]}\n  Subject: {email.get('subject', '(no subject)')[:60]}")
    
    # Format key events for the prompt
    event_highlights = []
    for event in data.get("events", [])[:10]:  # Top 10
        event_highlights.append(f"- {event.get('start_time', '')[:16]}: {event.get('summary', '(no title)')[:50]}")
    
    fallback_note = ""
    if use_mcp_fallback:
        fallback_note = """
## FALLBACK MODE
Server-side data collection had issues. You have MCP connectors enabled as backup.
Use gmail and google-calendar MCPs if you need to fetch additional data.
"""
    
    # Build task verification section
    task_verification_section = "No task verification data available."
    if verification_result:
        stats = verification_result.get("stats", {})
        impressions = verification_result.get("impressions", [])
        
        task_lines = []
        task_lines.append(f"Tasks verified: {stats.get('total', 0)} (Kept: {stats.get('kept', 0)}, Discarded: {stats.get('discarded', 0)})")
        
        if impressions:
            task_lines.append("\n**Daily Impressions Generated:**")
            for imp in impressions[:5]:  # Top 5
                task_lines.append(f"- [{imp.get('category', 'theme').upper()}] {imp.get('content', '')[:100]}")
        
        task_verification_section = "\n".join(task_lines)
    
    task_prompt = f"""# ATHENA THINKING SESSION - {today}

## SERVER-SIDE DATA COLLECTED
The athena-server has already collected data using your credentials:
- {email_summary}
- {event_summary}

### Email Highlights
{chr(10).join(email_highlights) if email_highlights else "No unread emails"}

### Upcoming Events
{chr(10).join(event_highlights) if event_highlights else "No upcoming events"}

{fallback_note}

## YOUR THINKING TASKS

This session is your workspace to think, analyze, and prepare. Bradley will see this session, so broadcast your thinking clearly.

### 1. Analyze the Data
- Review the emails above. Which are urgent? Which are from VIPs?
- Review the calendar. What prep is needed for meetings?
- Are there any patterns or concerns?

### 2. Generate Insights
- Use your tiered thinking (Tier 1 classify, Tier 2 patterns, Tier 3 synthesis)
- What should Bradley prioritize today?
- Any anomalies or important changes?

### 3. Prepare for Agenda & Workspace
- Draft the morning brief structure
- Queue any pending actions that need Bradley's approval
- Prepare any questions you want to ask Bradley (for your learning)

### 4. Task Verification Results
{task_verification_section}

### 5. Log Your Learnings
- If you notice patterns or learn something new, call POST /api/brain/evolution
- Record any performance observations

## BRAIN API
Base URL: https://athena-server-0dce.onrender.com/api
Auth: Bearer athena_api_key_2024

- GET /brain/full-context - Your complete context
- POST /brain/evolution - Propose learnings
- POST /brain/actions - Queue actions for approval

## REMEMBER
- This is YOUR thinking space - be thorough
- Bradley can see this, so explain your reasoning
- Don't ask Bradley questions here - save those for Agenda & Workspace
- Focus on analysis and preparation
"""
    
    # Determine connectors
    connectors = MANUS_CONNECTORS if use_mcp_fallback else ["notion"]
    
    result = await create_manus_task(
        task_prompt=task_prompt,
        model=settings.MANUS_MODEL_FULL,
        connectors=connectors,
        session_type='athena_thinking'
    )
    
    if result and result.get('id'):
        await rename_manus_task(result['id'], session_name)
    
    return result


async def send_failure_alert(error_message: str) -> None:
    """
    Send an alert to Bradley when ATHENA THINKING fails.
    Creates a Manus session with the error details.
    """
    logger.error(f"ATHENA THINKING failed: {error_message}")
    
    today = datetime.now().strftime("%B %d, %Y")
    
    alert_prompt = f"""# ATHENA THINKING FAILURE ALERT - {today}

## What Happened
ATHENA THINKING encountered an error and could not complete successfully.

## Error Details
{error_message}

## What This Means
- The morning brief may be incomplete
- Some data may not have been collected
- Manual review may be needed

## Recommended Actions
1. Check the athena-server logs on Render
2. Verify Gmail/Calendar OAuth tokens are valid
3. Check Neon database connectivity

## Recovery
The Agenda & Workspace session will still run at 6:05 AM, but may have limited data.

I apologize for the disruption. Please let me know if you need me to investigate further.
"""
    
    result = await create_manus_task(
        task_prompt=alert_prompt,
        model=settings.MANUS_MODEL_LITE,
        connectors=["notion"],
        session_type='general'
    )
    
    if result and result.get('id'):
        await rename_manus_task(result['id'], f"⚠️ ATHENA ALERT - {today}")


async def run_athena_thinking() -> Dict:
    """
    Main entry point for ATHENA THINKING job.
    
    Flow:
    1. Check brain status
    2. Collect data server-side
    3. Store observations in Neon
    4. Spawn Manus session for broadcast/reasoning
    5. Handle failures with alerts
    
    Returns:
        Result dict with status and details
    """
    logger.info("=" * 60)
    logger.info("Starting ATHENA THINKING job...")
    logger.info("=" * 60)
    
    result = {
        "status": "success",
        "server_side": {},
        "manus_session": {},
        "errors": []
    }
    
    # Check brain status
    try:
        status = get_brain_status()
        if not status or status.get('status') != 'active':
            logger.warning(f"Brain status is not active: {status}")
            result["errors"].append("Brain not active")
    except Exception as e:
        logger.error(f"Failed to check brain status: {e}")
        result["errors"].append(f"Brain check failed: {str(e)}")
    
    # Collect data server-side
    try:
        data = await collect_server_side_data()
        result["server_side"] = {
            "emails": len(data.get("emails", [])),
            "events": len(data.get("events", [])),
            "success": data.get("success", False),
            "errors": data.get("errors", [])
        }
        
        # Store observations
        if data.get("emails") or data.get("events"):
            obs_count = store_observations(data)
            result["server_side"]["observations_stored"] = obs_count
        
    except Exception as e:
        logger.error(f"Server-side collection failed: {e}")
        result["server_side"]["success"] = False
        result["server_side"]["errors"] = [str(e)]
        data = {"emails": [], "events": [], "errors": [str(e)], "success": False}
    
    # Run task verification and generate impressions
    verification_result = None
    try:
        logger.info("Running task verification...")
        verification_result = await run_task_verification(
            emails=data.get("emails", []),
            calendar_events=data.get("events", [])
        )
        result["task_verification"] = verification_result.get("stats", {})
        
        # Store impressions in brain
        impressions = verification_result.get("impressions", [])
        if impressions:
            from datetime import date
            stored_ids = store_daily_impressions_batch(date.today(), impressions)
            result["impressions_stored"] = len(stored_ids)
            logger.info(f"Stored {len(stored_ids)} impressions in brain")
        
    except Exception as e:
        logger.error(f"Task verification failed: {e}")
        result["errors"].append(f"Task verification: {str(e)}")
    
    # Spawn Manus session
    try:
        use_fallback = not data.get("success", False)
        manus_result = await spawn_thinking_session(
            data, 
            use_mcp_fallback=use_fallback,
            verification_result=verification_result
        )
        
        if manus_result:
            task_id = manus_result.get('id')
            result["manus_session"] = {
                "task_id": task_id,
                "task_url": f"https://manus.im/app/{task_id}",
                "fallback_mode": use_fallback
            }
            logger.info(f"Manus session created: {task_id}")
            
            # Update session state
            try:
                update_session_state(
                    session_type='athena_thinking',
                    handoff_context={
                        'created_at': datetime.utcnow().isoformat(),
                        'task_id': task_id,
                        'server_side_data': result["server_side"]
                    }
                )
            except Exception as state_error:
                logger.warning(f"Failed to update session state: {state_error}")
        else:
            result["status"] = "partial"
            result["errors"].append("Failed to create Manus session")
            
    except Exception as e:
        logger.error(f"Failed to spawn Manus session: {e}")
        result["status"] = "failed"
        result["errors"].append(f"Manus session failed: {str(e)}")
    
    # Send alert if failed
    if result["status"] == "failed":
        try:
            error_summary = "\n".join(result["errors"])
            await send_failure_alert(error_summary)
        except Exception as alert_error:
            logger.error(f"Failed to send failure alert: {alert_error}")
    
    logger.info(f"ATHENA THINKING complete: {result['status']}")
    logger.info("=" * 60)
    
    return result
