"""
Athena Server v2 - Weekly Rebuild Job
Fresh synthesis from raw observations to prevent drift.
Runs every Sunday at midnight.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict
import json

from anthropic import Anthropic

from config import settings
from db.neon import store_synthesis, get_canonical_memory, db_cursor

logger = logging.getLogger("athena.jobs.weekly")


def get_week_observations() -> list:
    """Get all observations from the past week."""
    with db_cursor() as cursor:
        cursor.execute("""
            SELECT * FROM observations 
            WHERE observed_at >= NOW() - INTERVAL '7 days'
            ORDER BY observed_at DESC
        """)
        return cursor.fetchall()


def get_week_patterns() -> list:
    """Get all patterns from the past week."""
    with db_cursor() as cursor:
        cursor.execute("""
            SELECT * FROM patterns 
            WHERE detected_at >= NOW() - INTERVAL '7 days'
            ORDER BY detected_at DESC
        """)
        return cursor.fetchall()


def generate_weekly_synthesis(
    client: Anthropic,
    observations: list,
    patterns: list,
    canonical_memory: list
) -> Dict:
    """
    Generate a comprehensive weekly synthesis.
    This is a fresh analysis from raw data to prevent drift.
    """
    # Summarize observations by category
    obs_by_category = {}
    for obs in observations:
        cat = obs['category']
        if cat not in obs_by_category:
            obs_by_category[cat] = []
        obs_by_category[cat].append({
            'summary': obs['summary'],
            'priority': obs['priority'],
            'source': obs['source']
        })
    
    # Summarize patterns
    pattern_summary = []
    for p in patterns:
        pattern_summary.append({
            'type': p['pattern_type'],
            'description': p['description'],
            'confidence': float(p['confidence']) if p['confidence'] else 0.0
        })
    
    prompt = f"""You are Athena, Bradley Hope's cognitive extension. Generate a WEEKLY synthesis.

This is a FRESH analysis from raw observations - not building on previous synthesis.
Purpose: Prevent drift by re-analyzing from ground truth.

WEEK'S OBSERVATIONS BY CATEGORY:
{json.dumps(obs_by_category, indent=2, default=str)}

WEEK'S PATTERNS:
{json.dumps(pattern_summary, indent=2)}

CANONICAL MEMORY (approved facts):
{json.dumps([{'category': cm['category'], 'content': cm.get('content', '')[:100]} for cm in canonical_memory[:10]], indent=2)}

Generate a comprehensive WEEKLY synthesis:

1. WEEK IN REVIEW
   - Major themes and activities
   - Key accomplishments
   - Challenges faced

2. PATTERN ANALYSIS
   - Recurring patterns observed
   - New patterns emerging
   - Patterns that have changed

3. RELATIONSHIP INSIGHTS
   - Key people interacted with
   - Communication patterns
   - Relationship health signals

4. PRODUCTIVITY ANALYSIS
   - Time allocation patterns
   - Focus areas
   - Potential improvements

5. RECOMMENDATIONS FOR NEXT WEEK
   - Priorities to focus on
   - Patterns to break or reinforce
   - People to follow up with

Respond in JSON format:
{{
    "executive_summary": "...",
    "key_insights": ["insight1", "insight2", ...],
    "questions_for_user": ["question1", ...],
    "memory_proposals": [{{"category": "...", "content": "...", "justification": "..."}}],
    "action_recommendations": ["action1", ...]
}}"""

    try:
        response = client.messages.create(
            model=settings.TIER3_MODEL,
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        content = response.content[0].text
        
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        
        return json.loads(content)
        
    except Exception as e:
        logger.error(f"Weekly synthesis generation failed: {e}")
        return {
            "executive_summary": f"Weekly synthesis failed: {str(e)}",
            "key_insights": [],
            "questions_for_user": [],
            "memory_proposals": [],
            "action_recommendations": []
        }


async def run_weekly_rebuild():
    """
    Run weekly synthesis rebuild.
    Fresh analysis from raw observations to prevent drift.
    """
    logger.info("Starting weekly synthesis rebuild...")
    start_time = datetime.utcnow()
    
    # Gather week's data
    observations = get_week_observations()
    patterns = get_week_patterns()
    canonical_memory = get_canonical_memory()
    
    if not observations:
        logger.info("No observations from the past week")
        return {"status": "skipped", "reason": "no_data"}
    
    logger.info(f"Rebuilding from {len(observations)} observations and {len(patterns)} patterns")
    
    # Initialize Anthropic client
    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    
    # Generate weekly synthesis
    synthesis_result = generate_weekly_synthesis(
        client,
        observations,
        patterns,
        canonical_memory
    )
    
    # Store synthesis
    synthesis_data = {
        'synthesis_type': 'weekly_rebuild',
        'synthesis_number': 1,
        'executive_summary': synthesis_result['executive_summary'],
        'key_insights': json.dumps(synthesis_result['key_insights']),
        'questions_for_user': json.dumps(synthesis_result['questions_for_user']),
        'memory_proposals': json.dumps(synthesis_result['memory_proposals']),
        'action_recommendations': json.dumps(synthesis_result['action_recommendations']),
        'observations_count': len(observations),
        'patterns_count': len(patterns),
        'created_at': datetime.utcnow()
    }
    
    try:
        synthesis_id = store_synthesis(synthesis_data)
        logger.info(f"Stored weekly synthesis with ID {synthesis_id}")
    except Exception as e:
        logger.error(f"Failed to store weekly synthesis: {e}")
        return {"status": "error", "error": str(e)}
    
    duration = (datetime.utcnow() - start_time).total_seconds()
    logger.info(f"Weekly rebuild complete in {duration:.1f}s")
    
    return {
        "status": "success",
        "observations_processed": len(observations),
        "patterns_processed": len(patterns),
        "duration_seconds": duration
    }
