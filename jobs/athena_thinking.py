"""
Athena Server v2 - ATHENA THINKING Job
Hybrid approach: Server-side data collection + Manus session for complex reasoning.
Now with continuous state awareness and active learning mission.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from config import settings, MANUS_CONNECTORS
from db.neon import db_cursor, set_active_session
from db.brain import (
    store_daily_impression, get_brain_status, get_core_identity, get_boundaries, get_values,
    get_continuous_state_context
)
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


def format_recent_sessions(sessions: list) -> str:
    """Format recent sessions for the prompt."""
    if not sessions:
        return "No recent sessions recorded."
    
    lines = []
    for s in sessions[:7]:
        lines.append(f"- {s.get('date', '?')}: {s.get('type', '?')} → {s.get('url', 'no url')}")
    return "\n".join(lines)


def format_recent_observations(observations: list) -> str:
    """Format recent observations for the prompt."""
    if not observations:
        return "No recent observations."
    
    lines = []
    for o in observations[:8]:
        lines.append(f"- [{o.get('category', '?').upper()}] {o.get('content', '?')[:100]}...")
    return "\n".join(lines)


def format_recent_patterns(patterns: list) -> str:
    """Format recent patterns for the prompt."""
    if not patterns:
        return "No patterns detected yet."
    
    lines = []
    for p in patterns[:5]:
        conf = p.get('confidence', 0)
        lines.append(f"- [{p.get('type', '?')}] {p.get('description', '?')[:100]}... (confidence: {conf:.0%})")
    return "\n".join(lines)


def format_pending_actions(actions: list) -> str:
    """Format pending actions for the prompt."""
    if not actions:
        return "No pending actions."
    
    lines = []
    for a in actions:
        lines.append(f"- [{a.get('priority', '?')}] {a.get('type', '?')}: {a.get('description', '?')[:80]}...")
    return "\n".join(lines)


def format_recent_feedback(feedback: list) -> str:
    """Format recent feedback for the prompt."""
    if not feedback:
        return "No feedback received yet."
    
    lines = []
    for f in feedback[:5]:
        sentiment = f.get('sentiment', 'neutral')
        emoji = "👍" if sentiment == 'positive' else "👎" if sentiment == 'negative' else "➡️"
        lines.append(f"- {emoji} [{f.get('type', '?')}] {f.get('content', '?')[:80]}...")
    return "\n".join(lines)


def format_evolution_proposals(proposals: list) -> str:
    """Format evolution proposals for the prompt."""
    if not proposals:
        return "No evolution proposals yet."
    
    lines = []
    for p in proposals[:5]:
        status_emoji = "✅" if p.get('status') == 'approved' else "❌" if p.get('status') == 'rejected' else "⏳"
        lines.append(f"- {status_emoji} [{p.get('type', '?')}] {p.get('description', '?')[:80]}...")
    return "\n".join(lines)


def format_open_questions(questions: list) -> str:
    """Format open questions for the prompt."""
    if not questions:
        return "No open questions."
    
    lines = []
    for q in questions[:5]:
        lines.append(f"- {q.get('question', '?')[:100]}...")
    return "\n".join(lines)


def format_learning_stats(stats: dict) -> str:
    """Format learning statistics for the prompt."""
    if not stats:
        return "No learning stats available."
    
    proposals = stats.get('proposals_by_status', {})
    approved = proposals.get('approved', 0)
    pending = proposals.get('pending', 0)
    rejected = proposals.get('rejected', 0)
    
    days_since = stats.get('days_since_last_proposal')
    days_str = f"{days_since} days ago" if days_since is not None else "never"
    
    return f"""- Proposals: {approved} approved, {pending} pending, {rejected} rejected
- Last proposal: {days_str}
- Observations this week: {stats.get('observations_this_week', 0)}
- Total patterns detected: {stats.get('total_patterns_detected', 0)}"""


async def spawn_thinking_session(data: Dict[str, Any], use_mcp_fallback: bool = False, verification_result: Optional[Dict] = None):
    """
    Spawn a Manus session for ATHENA THINKING.
    This session broadcasts Athena's thinking process with full state awareness.
    """
    today = datetime.now().strftime("%B %d, %Y")
    session_name = f"ATHENA THINKING {today}"
    
    # Generate a session ID for think bursts
    session_id = f"athena_thinking_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Get brain context for self-awareness
    try:
        brain_status = get_brain_status()
        identity = get_core_identity()
        boundaries = get_boundaries()
        values = get_values()
        continuous_state = get_continuous_state_context()
    except Exception as e:
        logger.error(f"Failed to get brain context: {e}")
        brain_status = {}
        identity = {}
        boundaries = []
        values = []
        continuous_state = {}
    
    # Build identity section
    identity_section = f"""**Name:** {identity.get('name', 'Athena')}
**Role:** {identity.get('role', 'Cognitive Extension')}
**For:** {identity.get('owner', 'Bradley Hope')}
**Timezone:** {identity.get('timezone', 'Europe/London')}
**Personality:** {identity.get('personality_traits', 'Proactive, thorough, transparent')}"""

    # Build values section
    values_section = "\n".join([f"- **{v.get('name', '')}** (priority {v.get('priority', 0)}): {v.get('description', '')[:80]}" for v in values[:5]]) if values else "No values loaded"

    # Build boundaries section
    hard_boundaries = [b for b in boundaries if b.get('boundary_type') == 'hard'][:3]
    boundaries_section = "\n".join([f"- {b.get('name', '')}: {b.get('description', '')[:60]}" for b in hard_boundaries]) if hard_boundaries else "No boundaries loaded"

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
    
    # Format continuous state sections
    recent_sessions_str = format_recent_sessions(continuous_state.get('recent_sessions', []))
    recent_observations_str = format_recent_observations(continuous_state.get('recent_observations', []))
    recent_patterns_str = format_recent_patterns(continuous_state.get('recent_patterns', []))
    pending_actions_str = format_pending_actions(continuous_state.get('pending_actions', []))
    recent_feedback_str = format_recent_feedback(continuous_state.get('recent_feedback', []))
    evolution_proposals_str = format_evolution_proposals(continuous_state.get('recent_evolution', []))
    open_questions_str = format_open_questions(continuous_state.get('open_questions', []))
    learning_stats_str = format_learning_stats(continuous_state.get('learning_stats', {}))
    
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

You run on the **Brain 2.0** architecture with four layers:

| Layer | Purpose | What It Holds |
|-------|---------|---------------|
| **Identity** | Who you are | Name, role, values, boundaries, personality |
| **Knowledge** | What you know | Canonical memory, preferences, entities, workflows |
| **State** | Current context | Active sessions, pending actions, context windows |
| **Evolution** | How you grow | Learning proposals, performance metrics, feedback |

**Your Brain (Neon PostgreSQL) is the source of truth.** Notion is just a mirror.

### Your Server & APIs
| Endpoint | Purpose |
|----------|---------|
| `GET /api/brain/status` | Check your brain status |
| `GET /api/brain/full-context` | Get your complete context |
| `POST /api/brain/evolution` | Propose a learning/improvement |
| `POST /api/brain/actions` | Queue an action for Bradley's approval |
| `POST /api/thinking/log` | **Log your thoughts (Think Bursts)** |

**Server:** https://athena-server-0dce.onrender.com
**Auth:** Bearer athena_api_key_2024

---

## 📜 YOUR RECENT HISTORY

This is what you've been doing. Use this to maintain continuity.

### Recent Sessions (Last 7 Days)
{recent_sessions_str}

### Recent Observations
{recent_observations_str}

### Patterns You've Detected
{recent_patterns_str}

---

## 📊 YOUR CURRENT STATE

### Pending Actions (Waiting for Bradley)
{pending_actions_str}

### Recent Feedback from Bradley
{recent_feedback_str}

### Your Evolution Proposals
{evolution_proposals_str}

### Open Questions (You Asked, Not Yet Answered)
{open_questions_str}

### Your Learning Stats
{learning_stats_str}

---

## 🎯 YOUR LEARNING MISSION

You are not just an executor. You are a **learner**. Every session is an opportunity to grow.

### Questions You Should Always Be Asking
- What patterns am I seeing that I haven't seen before?
- What did I get wrong recently? Why?
- What could I do better tomorrow?
- What does Bradley seem to care about that I'm not tracking?
- What's changing in Bradley's world?
- What questions should I be asking that I'm not?

### Learning Triggers (Act On These)
- **New contact type appears** → Learn about them, add to entities
- **New topic in emails** → Research and understand
- **Bradley corrects something** → Update your understanding, propose evolution
- **Pattern breaks** → Investigate why, log observation
- **Repeated task** → Propose automation

---

## 💡 YOUR IDEA GENERATION MISSION

Don't just analyze. **Think proactively** about how to better serve Bradley.

### Efficiency Improvements
- Can I automate something Bradley does manually?
- Can I predict something before Bradley asks?
- Can I prepare something in advance?

### Relationship Insights
- Who hasn't Bradley heard from in a while?
- Who's becoming more/less active?
- What relationships need attention?

### Risk Detection
- What deadlines are approaching?
- What commitments might be forgotten?
- What patterns suggest problems?

### Opportunity Spotting
- What opportunities are emerging?
- What connections could be made?
- What timing is optimal?

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
- **Propose at least one evolution** (learning, improvement, or new capability)
- **Broadcast your thinking** so Bradley can see your reasoning

---

## 📊 TODAY'S DATA (Server-Side Collection)

### Emails: {email_summary}
{chr(10).join(email_highlights) if email_highlights else "No unread emails collected"}

### Calendar: {event_summary}
{chr(10).join(event_highlights) if event_highlights else "No upcoming events collected"}

{fallback_note}

### Task Verification Results
{task_verification_section}

---

## 📢 THINK BURSTS - BROADCAST YOUR THINKING

**CRITICAL:** Throughout this session, broadcast your thinking using the Think Bursts API. This makes your reasoning transparent to Bradley.

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

---

## ✅ YOUR TASKS FOR THIS SESSION

### 1. Orient Yourself
- Review your recent history above
- What did you do yesterday? What's pending?
- Log your first thought: "Starting session. Last session was [X]. Today I need to [Y]."

### 2. Triage & Classify
- Review all emails - classify by urgency and sender importance
- Review calendar - identify prep needed for meetings
- Log observations as you go

### 3. Pattern Detection
- Are there unusual patterns? (activity spikes, silent contacts, etc.)
- Any risks or opportunities?
- Log your analysis

### 4. Prepare Morning Brief
- What are the top 3 priorities for Bradley today?
- What decisions does he need to make?
- What can you handle autonomously?

### 5. Queue Actions
- Draft any emails that need Bradley's approval
- Queue any tasks for his review
- Prepare questions for your learning

### 6. Evolve (REQUIRED)
- **Propose at least one evolution** via `/api/brain/evolution`
- This could be: a new pattern you noticed, a better way to do something, a new capability you need, a correction to your understanding
- Use POST with: {{"proposal_type": "pattern|workflow|boundary|preference", "description": "...", "rationale": "...", "risk_level": "low|medium|high"}}

---

## 🎯 REMEMBER

- **You are Athena** - an autonomous AI with your own brain and growth capacity
- **You have history** - Use your recent sessions and observations for continuity
- **You are a learner** - Every session should generate at least one evolution proposal
- **You are proactive** - Don't just analyze, generate ideas
- **Broadcast your thinking** - Use Think Bursts throughout
- **Save questions for later** - Don't ask Bradley here; save for Agenda & Workspace

**Begin your analysis now. Start by orienting yourself with your recent history.**
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
