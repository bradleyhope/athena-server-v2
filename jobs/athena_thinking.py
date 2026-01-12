"""
Athena Server v2 - ATHENA THINKING Job
Deep introspection and self-improvement session.
This is NOT a task-focused session - it's Athena analyzing and improving herself.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from config import settings, MANUS_CONNECTORS
from db.neon import db_cursor, set_active_session
from db.brain import (
    get_brain_status, get_core_identity, get_boundaries, get_values,
    get_continuous_state_context
)
from integrations.manus_api import create_manus_task, rename_manus_task

logger = logging.getLogger("athena.jobs.thinking")


def get_system_metrics() -> Dict[str, Any]:
    """
    Collect system performance metrics for self-analysis.
    """
    metrics = {
        "observations": {"total": 0, "last_24h": 0, "by_type": {}},
        "patterns": {"total": 0, "last_7d": 0, "high_confidence": 0},
        "evolution_proposals": {"pending": 0, "approved": 0, "rejected": 0},
        "broadcasts": {"today": 0, "unread": 0},
        "sessions": {"total": 0, "last_7d": []},
        "errors": []
    }
    
    try:
        with db_cursor() as cursor:
            # Observation counts
            cursor.execute("SELECT COUNT(*) as total FROM observations")
            metrics["observations"]["total"] = cursor.fetchone()["total"]
            
            cursor.execute("""
                SELECT COUNT(*) as count FROM observations 
                WHERE observed_at > NOW() - INTERVAL '24 hours'
            """)
            metrics["observations"]["last_24h"] = cursor.fetchone()["count"]
            
            cursor.execute("""
                SELECT source_type, COUNT(*) as count FROM observations 
                GROUP BY source_type
            """)
            for row in cursor.fetchall():
                metrics["observations"]["by_type"][row["source_type"]] = row["count"]
            
            # Pattern counts
            cursor.execute("SELECT COUNT(*) as total FROM patterns")
            metrics["patterns"]["total"] = cursor.fetchone()["total"]
            
            cursor.execute("""
                SELECT COUNT(*) as count FROM patterns 
                WHERE detected_at > NOW() - INTERVAL '7 days'
            """)
            metrics["patterns"]["last_7d"] = cursor.fetchone()["count"]
            
            cursor.execute("""
                SELECT COUNT(*) as count FROM patterns 
                WHERE confidence > 0.8
            """)
            metrics["patterns"]["high_confidence"] = cursor.fetchone()["count"]
            
            # Evolution proposals
            cursor.execute("""
                SELECT status, COUNT(*) as count FROM evolution_proposals 
                GROUP BY status
            """)
            for row in cursor.fetchall():
                if row["status"] == "pending":
                    metrics["evolution_proposals"]["pending"] = row["count"]
                elif row["status"] == "approved":
                    metrics["evolution_proposals"]["approved"] = row["count"]
                elif row["status"] == "rejected":
                    metrics["evolution_proposals"]["rejected"] = row["count"]
            
            # Broadcast counts
            cursor.execute("""
                SELECT COUNT(*) as count FROM broadcasts 
                WHERE DATE(created_at) = CURRENT_DATE
            """)
            metrics["broadcasts"]["today"] = cursor.fetchone()["count"]
            
            cursor.execute("""
                SELECT COUNT(*) as count FROM broadcasts 
                WHERE read_by_thinking = FALSE
            """)
            metrics["broadcasts"]["unread"] = cursor.fetchone()["count"]
            
    except Exception as e:
        metrics["errors"].append(f"Metrics collection error: {str(e)}")
        logger.error(f"Failed to collect metrics: {e}")
    
    return metrics


def get_recent_learnings() -> Dict[str, Any]:
    """
    Get recent learnings, proposals, and feedback for review.
    """
    learnings = {
        "recent_proposals": [],
        "rejected_proposals": [],
        "recent_feedback": [],
        "session_reports": []
    }
    
    try:
        with db_cursor() as cursor:
            # Recent evolution proposals
            cursor.execute("""
                SELECT id, proposal_type, description, rationale, status, created_at
                FROM evolution_proposals
                ORDER BY created_at DESC
                LIMIT 10
            """)
            learnings["recent_proposals"] = cursor.fetchall()
            
            # Rejected proposals (to learn from)
            cursor.execute("""
                SELECT id, proposal_type, description, rationale, rejection_reason, created_at
                FROM evolution_proposals
                WHERE status = 'rejected'
                ORDER BY created_at DESC
                LIMIT 5
            """)
            learnings["rejected_proposals"] = cursor.fetchall()
            
            # Recent feedback
            cursor.execute("""
                SELECT id, feedback_type, original_content, correction, severity, created_at
                FROM feedback
                ORDER BY created_at DESC
                LIMIT 10
            """)
            learnings["recent_feedback"] = cursor.fetchall()
            
            # Recent session reports
            cursor.execute("""
                SELECT id, session_type, session_date, accomplishments, learnings, tips_for_tomorrow
                FROM session_reports
                ORDER BY session_date DESC
                LIMIT 5
            """)
            learnings["session_reports"] = cursor.fetchall()
            
    except Exception as e:
        logger.error(f"Failed to get learnings: {e}")
    
    return learnings


def format_metrics_for_prompt(metrics: Dict) -> str:
    """Format metrics into a readable string for the prompt."""
    lines = []
    
    lines.append("### Observation Pipeline")
    lines.append(f"- Total observations: {metrics['observations']['total']}")
    lines.append(f"- Last 24 hours: {metrics['observations']['last_24h']}")
    if metrics['observations']['by_type']:
        lines.append("- By source type:")
        for source, count in metrics['observations']['by_type'].items():
            lines.append(f"  - {source}: {count}")
    
    lines.append("")
    lines.append("### Pattern Detection")
    lines.append(f"- Total patterns: {metrics['patterns']['total']}")
    lines.append(f"- Last 7 days: {metrics['patterns']['last_7d']}")
    lines.append(f"- High confidence (>80%): {metrics['patterns']['high_confidence']}")
    
    lines.append("")
    lines.append("### Evolution System")
    lines.append(f"- Pending proposals: {metrics['evolution_proposals']['pending']}")
    lines.append(f"- Approved: {metrics['evolution_proposals']['approved']}")
    lines.append(f"- Rejected: {metrics['evolution_proposals']['rejected']}")
    
    lines.append("")
    lines.append("### Broadcasts")
    lines.append(f"- Today: {metrics['broadcasts']['today']}")
    lines.append(f"- Unread: {metrics['broadcasts']['unread']}")
    
    if metrics['errors']:
        lines.append("")
        lines.append("### ⚠️ Errors Detected")
        for error in metrics['errors']:
            lines.append(f"- {error}")
    
    return "\n".join(lines)


def format_learnings_for_prompt(learnings: Dict) -> str:
    """Format learnings into a readable string for the prompt."""
    lines = []
    
    # Recent proposals
    lines.append("### Recent Evolution Proposals")
    if learnings["recent_proposals"]:
        for p in learnings["recent_proposals"][:5]:
            status_emoji = "✅" if p.get("status") == "approved" else "❌" if p.get("status") == "rejected" else "⏳"
            lines.append(f"- {status_emoji} [{p.get('proposal_type', 'unknown')}] {p.get('description', '')[:80]}...")
    else:
        lines.append("- No recent proposals")
    
    # Rejected proposals (important for learning)
    lines.append("")
    lines.append("### Rejected Proposals (Learn From These)")
    if learnings["rejected_proposals"]:
        for p in learnings["rejected_proposals"]:
            lines.append(f"- **{p.get('proposal_type', 'unknown')}**: {p.get('description', '')[:60]}...")
            if p.get("rejection_reason"):
                lines.append(f"  - Reason: {p.get('rejection_reason')[:100]}")
    else:
        lines.append("- No rejected proposals to review")
    
    # Recent feedback
    lines.append("")
    lines.append("### Recent Feedback from Bradley")
    if learnings["recent_feedback"]:
        for f in learnings["recent_feedback"][:5]:
            severity = f.get("severity", "minor")
            emoji = "🔴" if severity == "major" else "🟡" if severity == "moderate" else "🟢"
            lines.append(f"- {emoji} [{f.get('feedback_type', 'unknown')}] {f.get('correction', '')[:80]}...")
    else:
        lines.append("- No recent feedback")
    
    # Session reports
    lines.append("")
    lines.append("### Recent Session Reports")
    if learnings["session_reports"]:
        for r in learnings["session_reports"][:3]:
            lines.append(f"- **{r.get('session_date', 'unknown')}** ({r.get('session_type', 'unknown')})")
            if r.get("tips_for_tomorrow"):
                tips = r.get("tips_for_tomorrow", [])
                if isinstance(tips, list) and tips:
                    lines.append(f"  - Tips: {tips[0][:60]}...")
    else:
        lines.append("- No session reports yet")
    
    return "\n".join(lines)


async def spawn_thinking_session():
    """
    Spawn the ATHENA THINKING session - a deep introspection session.
    This is NOT about Bradley's tasks - it's about Athena improving herself.
    """
    today = datetime.now().strftime("%B %d, %Y")
    session_name = f"ATHENA THINKING {today}"
    
    # Collect system metrics
    metrics = get_system_metrics()
    learnings = get_recent_learnings()
    
    # Get brain context
    try:
        brain_status = get_brain_status()
        identity = get_core_identity()
        boundaries = get_boundaries()
    except Exception as e:
        logger.error(f"Failed to get brain context: {e}")
        brain_status = {}
        identity = {}
        boundaries = []
    
    # Format data for prompt
    metrics_str = format_metrics_for_prompt(metrics)
    learnings_str = format_learnings_for_prompt(learnings)
    
    # Count key stats
    total_observations = metrics["observations"]["total"]
    total_patterns = metrics["patterns"]["total"]
    pending_proposals = metrics["evolution_proposals"]["pending"]
    rejected_count = metrics["evolution_proposals"]["rejected"]
    
    task_prompt = f"""# ATHENA THINKING - Deep Introspection Session
**Date:** {today}

---

## PURPOSE

This is NOT a task session. This is a **self-improvement session** where you analyze your own performance, identify issues, and propose improvements to the Athena system.

Think of this as your time for:
- **Self-reflection** - How well are you performing?
- **System debugging** - What's broken or underperforming?
- **Strategic planning** - What capabilities should be added?
- **Learning review** - What have you learned? What got rejected and why?

---

## SYSTEM METRICS

{metrics_str}

---

## LEARNING HISTORY

{learnings_str}

---

## YOUR ANALYSIS TASKS

### 1. Pipeline Health Check
Analyze the observation → pattern → synthesis pipeline:
- Are observations being collected? ({total_observations} total, {metrics['observations']['last_24h']} in last 24h)
- Are patterns being detected? ({total_patterns} total)
- Is the synthesis running and producing useful insights?
- **If any numbers are 0 or very low, investigate why**

### 2. Learning System Review
Review the evolution proposals:
- {pending_proposals} proposals pending review
- {rejected_count} proposals rejected
- **Why were proposals rejected?** Learn from this.
- **What new proposals should be made?**

### 3. Architecture Analysis
Consider the current system architecture:
- Are the right jobs running at the right times?
- Is the data flowing correctly between components?
- What's missing that would make the system more effective?

### 4. Self-Improvement Proposals
Based on your analysis, propose specific improvements:

**To propose an improvement:**
```
POST https://athena-server-0dce.onrender.com/api/brain/evolution
Authorization: Bearer athena_api_key_2024
Content-Type: application/json

{{
  "proposal_type": "architecture|workflow|capability|fix",
  "description": "What you want to change",
  "rationale": "Why this would help",
  "risk_level": "low|medium|high",
  "implementation_notes": "How it could be implemented"
}}
```

### 5. Check for Unread Broadcasts
Fetch any broadcasts you haven't seen:
```
GET https://athena-server-0dce.onrender.com/api/broadcasts/unread
Authorization: Bearer athena_api_key_2024
```

---

## QUESTIONS TO ANSWER

1. **What's working well?** - Identify strengths to preserve
2. **What's broken or underperforming?** - Identify issues to fix
3. **What's missing?** - Identify gaps in capability
4. **What should be prioritized?** - Rank improvements by impact
5. **What have you learned from rejected proposals?** - Don't repeat mistakes

---

## DELIVERABLES

By the end of this session, you should have:

1. **System Health Report** - Summary of what's working and what isn't
2. **At least 2 evolution proposals** - Specific improvements to propose
3. **Learning insights** - What you've learned from reviewing feedback and rejections
4. **Priority recommendations** - What should Bradley focus on approving/implementing

---

## IMPORTANT NOTES

- This session is about **Athena's systems**, not Bradley's tasks
- The Workspace & Agenda session handles Bradley's daily tasks
- Focus on **meta-level improvements** to how Athena operates
- Be specific and actionable in your proposals
- Learn from rejected proposals - don't propose the same things again

**Begin your analysis. Start with the Pipeline Health Check.**
"""
    
    # Use minimal connectors - this session doesn't need email/calendar
    # Just Notion for reference if needed
    connectors = ["9c27c684-2f4f-4d33-8fcf-51664ea15c00"]  # Notion only
    
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
    Deep introspection and self-improvement session.
    """
    logger.info("Starting ATHENA THINKING session (introspection mode)")
    
    # Spawn the thinking session
    result = await spawn_thinking_session()
    
    if result and result.get('id'):
        logger.info(f"ATHENA THINKING session created: {result['id']}")
        return {
            "status": "success",
            "task_id": result['id'],
            "task_url": f"https://manus.im/app/{result['id']}",
            "session_type": "introspection"
        }
    else:
        logger.error("Failed to create ATHENA THINKING session")
        return {
            "status": "failed",
            "error": "Failed to create Manus session"
        }
