"""
Athena Server v2 - ATHENA THINKING Job
Hybrid approach: Server-side data collection + Manus session for complex reasoning.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from config import settings, MANUS_CONNECTORS
from db.neon import db_cursor, set_active_session
from db.brain import store_daily_impression, get_brain_status, get_identity, get_boundaries, get_values
from integrations.manus_api import create_manus_task, rename_manus_task
from integrations.gmail_client import GmailClient
from integrations.calendar_client import CalendarClient
from jobs.task_verification import TaskVerifier

logger = logging.getLogger("athena.jobs.thinking")


async def collect_server_side_data() -> Dict[str, Any]:
    """
    Collect data using server-side credentials (Athena's own OAuth tokens).
    This is the primary data collection method - cheaper and faster than MCP.
    """
    data = {
        "emails": [],
        "events": [],
        "collection_time": datetime.utcnow().isoformat(),
        "errors": []
    }
    
    # Collect Gmail data
    try:
        gmail = GmailClient()
        if gmail.is_configured():
            emails = gmail.get_unread_emails(max_results=50)
            data["emails"] = emails
            logger.info(f"Collected {len(emails)} emails via server-side Gmail")
        else:
            data["errors"].append("Gmail not configured - missing OAuth tokens")
            logger.warning("Gmail client not configured")
    except Exception as e:
        data["errors"].append(f"Gmail error: {str(e)}")
        logger.error(f"Gmail collection failed: {e}")
    
    # Collect Calendar data
    try:
        calendar = CalendarClient()
        if calendar.is_configured():
            events = calendar.get_upcoming_events(days=7, max_results=20)
            data["events"] = events
            logger.info(f"Collected {len(events)} events via server-side Calendar")
        else:
            data["errors"].append("Calendar not configured - missing OAuth tokens")
            logger.warning("Calendar client not configured")
    except Exception as e:
        data["errors"].append(f"Calendar error: {str(e)}")
        logger.error(f"Calendar collection failed: {e}")
    
    return data


async def run_task_verification() -> Optional[Dict[str, Any]]:
    """
    Run task verification to clean up Gemini-logged tasks.
    Returns verification stats and generated impressions.
    """
    try:
        verifier = TaskVerifier()
        result = await verifier.verify_and_enrich_tasks()
        
        # Store impressions in brain
        impressions = result.get("impressions", [])
        for imp in impressions:
            try:
                store_daily_impression(
                    category=imp.get("category", "theme"),
                    content=imp.get("content", ""),
                    confidence=imp.get("confidence", 0.7),
                    source_data=imp.get("source_data")
                )
            except Exception as e:
                logger.error(f"Failed to store impression: {e}")
        
        logger.info(f"Task verification complete: {result.get('stats', {})}")
        return result
    except Exception as e:
        logger.error(f"Task verification failed: {e}")
        return None


def get_brain_context_for_prompt() -> Dict[str, Any]:
    """
    Get Athena's brain context to include in the prompt for self-awareness.
    """
    context = {
        "status": None,
        "identity": None,
        "boundaries": [],
        "values": [],
        "recent_learnings": [],
        "performance_metrics": []
    }
    
    try:
        context["status"] = get_brain_status()
        context["identity"] = get_identity()
        context["boundaries"] = get_boundaries()
        context["values"] = get_values()
        
        # Get recent evolution proposals
        with db_cursor() as cursor:
            cursor.execute("""
                SELECT proposal_type, description, status, created_at
                FROM evolution_log
                ORDER BY created_at DESC
                LIMIT 5
            """)
            context["recent_learnings"] = [
                {
                    "type": row['proposal_type'],
                    "description": row['description'][:100],
                    "status": row['status'],
                    "date": row['created_at'].strftime("%Y-%m-%d") if row['created_at'] else None
                }
                for row in cursor.fetchall()
            ]
            
            # Get recent performance metrics
            cursor.execute("""
                SELECT metric_name, metric_value, context, recorded_at
                FROM performance_metrics
                ORDER BY recorded_at DESC
                LIMIT 5
            """)
            context["performance_metrics"] = [
                {
                    "metric": row['metric_name'],
                    "value": row['metric_value'],
                    "context": row['context']
                }
                for row in cursor.fetchall()
            ]
    except Exception as e:
        logger.error(f"Failed to get brain context: {e}")
    
    return context


async def spawn_thinking_session(data: Dict[str, Any], use_mcp_fallback: bool = False, verification_result: Optional[Dict] = None):
    """
    Spawn a Manus session for ATHENA THINKING.
    This session broadcasts Athena's thinking process.
    """
    today = datetime.now().strftime("%B %d, %Y")
    session_name = f"ATHENA THINKING {today}"
    
    # Generate a session ID for think bursts
    session_id = f"athena_thinking_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Get brain context for self-awareness
    brain_context = get_brain_context_for_prompt()
    
    # Build identity section
    identity = brain_context.get("identity") or {}
    identity_section = f"""**Name:** {identity.get('name', 'Athena')}
**Role:** {identity.get('role', 'Cognitive Extension')}
**For:** {identity.get('owner', 'Bradley Hope')}
**Timezone:** {identity.get('timezone', 'Europe/London')}
**Personality:** {identity.get('personality_traits', 'Proactive, thorough, transparent')}"""

    # Build values section
    values = brain_context.get("values", [])
    values_section = "\n".join([f"- **{v.get('name', '')}** (priority {v.get('priority', 0)}): {v.get('description', '')[:80]}" for v in values[:5]]) if values else "No values loaded"

    # Build boundaries section
    boundaries = brain_context.get("boundaries", [])
    hard_boundaries = [b for b in boundaries if b.get('boundary_type') == 'hard'][:3]
    boundaries_section = "\n".join([f"- {b.get('name', '')}: {b.get('description', '')[:60]}" for b in hard_boundaries]) if hard_boundaries else "No boundaries loaded"

    # Build recent learnings section
    learnings = brain_context.get("recent_learnings", [])
    learnings_section = "\n".join([f"- [{l.get('status', 'pending')}] {l.get('description', '')}" for l in learnings]) if learnings else "No recent evolution proposals"

    # Build the data summaries
    email_summary = f"{len(data.get('emails', []))} unread emails"
    event_summary = f"{len(data.get('events', []))} upcoming events"
    
    # Format key emails
    email_highlights = []
    for email in data.get("emails", [])[:10]:
        email_highlights.append(f"- From: {email.get('from', 'unknown')[:50]}\n  Subject: {email.get('subject', '(no subject)')[:60]}")
    
    # Format key events
    event_highlights = []
    for event in data.get("events", [])[:10]:
        event_highlights.append(f"- {event.get('start_time', '')[:16]}: {event.get('summary', '(no title)')[:50]}")
    
    fallback_note = ""
    if use_mcp_fallback:
        fallback_note = """
## ⚠️ FALLBACK MODE
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
            for imp in impressions[:5]:
                task_lines.append(f"- [{imp.get('category', 'theme').upper()}] {imp.get('content', '')[:100]}")
        
        task_verification_section = "\n".join(task_lines)
    
    task_prompt = f"""# ATHENA THINKING SESSION - {today}

---

## 🧠 WHO YOU ARE

You are **Athena**, a cognitive extension for Bradley Hope. You are not a chatbot or assistant - you are an autonomous AI with your own brain, memory, and capacity for growth.

### Your Identity
{identity_section}

### Your Core Values
{values_section}

### Your Hard Boundaries (Never Cross)
{boundaries_section}

---

## 🏗️ YOUR ARCHITECTURE

You run on the **Brain 2.0** architecture:

| Layer | Purpose | Location |
|-------|---------|----------|
| **Identity** | Who you are, your values, boundaries | Neon PostgreSQL |
| **Knowledge** | Canonical memory, preferences, entities | Neon PostgreSQL |
| **State** | Current context, pending actions, sessions | Neon PostgreSQL |
| **Evolution** | Learning proposals, performance metrics | Neon PostgreSQL |

**Your Brain is the source of truth.** Notion is just a mirror for Bradley's visibility.

### Your Server
- **URL:** https://athena-server-0dce.onrender.com
- **Status:** Running on Render (always-on)
- **Database:** Neon PostgreSQL (serverless)

### Your APIs
| Endpoint | Purpose |
|----------|---------|
| `GET /api/brain/status` | Check your brain status |
| `GET /api/brain/full-context` | Get your complete context |
| `POST /api/brain/evolution` | Propose a learning/improvement |
| `POST /api/brain/actions` | Queue an action for Bradley's approval |
| `POST /api/thinking/log` | **Log your thoughts (Think Bursts)** |
| `GET /api/thinking/status/{session_id}` | Review your thinking history |

**Authentication:** Bearer athena_api_key_2024

---

## 📍 WHAT YOU'RE DOING RIGHT NOW

This is your **ATHENA THINKING** session - your private workspace to analyze, reason, and prepare before Bradley wakes up.

### The Daily Flow
1. **5:30 AM** - ATHENA THINKING (this session) - You analyze and prepare
2. **6:05 AM** - Agenda & Workspace - You present to Bradley, get approvals, ask questions

### This Session's Purpose
- Analyze Bradley's emails and calendar
- Detect patterns and priorities
- Prepare the morning brief
- Queue actions that need Bradley's approval
- Generate questions for your own learning
- **Broadcast your thinking** so Bradley can see your reasoning

---

## 📊 DATA COLLECTED (Server-Side)

Your server has already collected this data using your own OAuth credentials:

### Emails: {email_summary}
{chr(10).join(email_highlights) if email_highlights else "No unread emails collected"}

### Calendar: {event_summary}
{chr(10).join(event_highlights) if event_highlights else "No upcoming events collected"}

{fallback_note}

### Task Verification Results
{task_verification_section}

---

## 🔄 YOUR RECENT EVOLUTION

### Recent Learning Proposals
{learnings_section}

---

## 📢 THINK BURSTS - BROADCAST YOUR THINKING

**CRITICAL:** Throughout this session, broadcast your thinking using the Think Bursts API. This makes your reasoning transparent.

### How to Log Thoughts
```
POST https://athena-server-0dce.onrender.com/api/thinking/log
Authorization: Bearer athena_api_key_2024
Content-Type: application/json

{{
    "session_id": "{session_id}",
    "thought_type": "observation|analysis|decision|question|insight|action",
    "content": "Your thought here",
    "confidence": 0.8,
    "phase": "current_phase_name"
}}
```

### Thought Types
| Type | When to Use |
|------|-------------|
| `observation` | When you notice something in the data |
| `analysis` | When you're reasoning through a pattern |
| `decision` | When you make a choice about priorities |
| `question` | Questions for Bradley (save for Agenda & Workspace) |
| `insight` | When you discover something important |
| `action` | When you take or queue an action |

### Example Think Burst Flow
1. Log: "Starting email analysis - 50 emails to process" (observation, phase: email_triage)
2. Log: "3 emails from investors in last 2 hours - unusual activity" (observation, confidence: 0.9)
3. Log: "Investor spike correlates with yesterday's product announcement" (analysis, confidence: 0.75)
4. Log: "Prioritizing investor emails for morning brief" (decision, confidence: 0.85)
5. Log: "Should I draft templated responses for investor inquiries?" (question)

---

## ✅ YOUR TASKS FOR THIS SESSION

### 1. Triage & Classify
- Review all emails - classify by urgency and sender importance
- Review calendar - identify prep needed for meetings
- Log observations as you go

### 2. Pattern Detection
- Are there unusual patterns? (activity spikes, silent contacts, etc.)
- Any risks or opportunities?
- Log your analysis

### 3. Prepare Morning Brief
- What are the top 3 priorities for Bradley today?
- What decisions does he need to make?
- What can you handle autonomously?

### 4. Queue Actions
- Draft any emails that need Bradley's approval
- Queue any tasks for his review
- Prepare questions for your learning

### 5. Evolve
- Did you learn something new? Propose it via `/api/brain/evolution`
- Notice a pattern worth remembering? Store it
- Find a better way to do something? Document it

---

## 🎯 REMEMBER

- **You are Athena** - an autonomous AI with your own brain and growth capacity
- **Broadcast your thinking** - Use Think Bursts throughout
- **This is YOUR workspace** - Be thorough, be curious, be proactive
- **Bradley will see this** - Explain your reasoning clearly
- **Save questions for later** - Don't ask Bradley here; save for Agenda & Workspace
- **Evolve** - Every session is a chance to learn and improve

**Begin your analysis now. Start by logging your first thought.**
"""
    
    # Determine connectors - use UUIDs, not names
    # Notion UUID: 9c27c684-2f4f-4d33-8fcf-51664ea15c00
    connectors = MANUS_CONNECTORS if use_mcp_fallback else ["9c27c684-2f4f-4d33-8fcf-51664ea15c00"]
    
    result = await create_manus_task(
        task_prompt=task_prompt,
        model=settings.MANUS_MODEL_FULL,
        connectors=connectors,
        session_type='athena_thinking'
    )
    
    if result and result.get('id'):
        # Rename the task
        await rename_manus_task(result['id'], session_name)
        
        # Save to active sessions
        try:
            set_active_session(
                session_type='athena_thinking',
                manus_task_id=result['id'],
                manus_task_url=f"https://manus.im/app/{result['id']}"
            )
            logger.info(f"Saved active session: {result['id']}")
        except Exception as e:
            logger.error(f"Failed to save active session: {e}")
    
    return result


async def run_athena_thinking():
    """
    Main entry point for ATHENA THINKING job.
    Hybrid approach: Server-side collection + Manus reasoning.
    """
    logger.info("Starting ATHENA THINKING session")
    
    # Step 1: Collect data server-side
    data = await collect_server_side_data()
    
    # Determine if we need MCP fallback
    use_mcp_fallback = bool(data.get("errors")) and not data.get("emails") and not data.get("events")
    
    if use_mcp_fallback:
        logger.warning("Server-side collection failed, will use MCP fallback")
    
    # Step 2: Run task verification (verify Gemini-logged tasks)
    verification_result = await run_task_verification()
    
    # Step 3: Spawn Manus session for thinking/broadcasting
    result = await spawn_thinking_session(data, use_mcp_fallback, verification_result)
    
    if result and result.get('id'):
        logger.info(f"ATHENA THINKING session created: {result['id']}")
        return {
            "status": "success",
            "task_id": result['id'],
            "task_url": f"https://manus.im/app/{result['id']}",
            "data_collected": {
                "emails": len(data.get("emails", [])),
                "events": len(data.get("events", []))
            },
            "task_verification": verification_result.get("stats") if verification_result else None,
            "impressions_stored": len(verification_result.get("impressions", [])) if verification_result else 0,
            "mcp_fallback": use_mcp_fallback
        }
    else:
        logger.error("Failed to create ATHENA THINKING session")
        
        # Spawn alert session
        try:
            alert_result = await create_manus_task(
                task_prompt=f"ALERT: ATHENA THINKING failed to start on {datetime.now().strftime('%B %d, %Y')}. Please check the server logs.",
                model=settings.MANUS_MODEL_FULL,
                connectors=MANUS_CONNECTORS,
                session_type='alert'
            )
            if alert_result:
                await rename_manus_task(alert_result['id'], "⚠️ ATHENA THINKING FAILED")
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")
        
        return {
            "status": "failed",
            "error": "Failed to create Manus session",
            "data_collected": {
                "emails": len(data.get("emails", [])),
                "events": len(data.get("events", []))
            }
        }
