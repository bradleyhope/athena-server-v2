"""
Athena Server v2 - Synthesis Job
Tier 3: Generate executive summaries and insights using Claude Sonnet 4.5.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
import json

from anthropic import Anthropic

from config import settings
from db.neon import (
    get_recent_observations,
    get_recent_patterns,
    get_latest_synthesis,
    get_canonical_memory,
    store_synthesis,
    db_cursor
)

logger = logging.getLogger("athena.jobs.synthesis")


def get_next_synthesis_number() -> int:
    """Get the next synthesis number for today."""
    with db_cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(*) as count FROM synthesis_memory 
            WHERE DATE(created_at) = CURRENT_DATE
        """)
        result = cursor.fetchone()
        return (result['count'] or 0) + 1


def generate_synthesis(
    client: Anthropic,
    observations: list,
    patterns: list,
    canonical_memory: list,
    previous_synthesis: Optional[Dict]
) -> Dict:
    """
    Generate a comprehensive synthesis using Claude Sonnet 4.5.
    """
    # Prepare context
    obs_summary = []
    for obs in observations[:50]:  # Limit to recent 50
        obs_summary.append({
            'source': obs['source_type'],
            'category': obs['category'],
            'priority': obs['priority'],
            'summary': obs['summary']
        })
    
    pattern_summary = []
    for p in patterns[:20]:
        pattern_summary.append({
            'type': p['pattern_type'],
            'description': p['description'],
            'confidence': float(p['confidence']) if p['confidence'] else 0.0
        })
    
    canonical_summary = []
    for cm in canonical_memory[:20]:
        canonical_summary.append({
            'category': cm['category'],
            'content': cm.get('content', '')[:200]
        })
    
    prev_summary = ""
    if previous_synthesis:
        prev_summary = f"""
PREVIOUS SYNTHESIS (for continuity):
{previous_synthesis.get('executive_summary', 'No previous synthesis')}
"""

    prompt = f"""You are Athena, Bradley Hope's cognitive extension. Generate a synthesis of recent activity.

RECENT OBSERVATIONS ({len(observations)} total):
{json.dumps(obs_summary, indent=2)}

DETECTED PATTERNS ({len(patterns)} total):
{json.dumps(pattern_summary, indent=2)}

CANONICAL MEMORY (approved facts):
{json.dumps(canonical_summary, indent=2)}

{prev_summary}

Generate a comprehensive synthesis with:

1. EXECUTIVE SUMMARY
   - What happened in the last period
   - What matters most right now
   - Key themes emerging

2. KEY INSIGHTS
   - Connections between observations
   - Patterns worth noting
   - Behavioral observations about Bradley's work

3. QUESTIONS FOR BRADLEY
   - Decisions that need his input
   - Clarifications needed
   - Things you're uncertain about

4. MEMORY PROPOSALS
   - New facts to add to canonical memory
   - Updates to existing memory
   - Each proposal needs clear justification

5. ACTION RECOMMENDATIONS
   - What Athena should do next
   - Emails to draft
   - Things to monitor

Respond in JSON format:
{{
    "executive_summary": "...",
    "key_insights": ["insight1", "insight2", ...],
    "questions_for_user": ["question1", "question2", ...],
    "memory_proposals": [
        {{"category": "...", "content": "...", "justification": "..."}}
    ],
    "action_recommendations": ["action1", "action2", ...]
}}"""

    try:
        logger.info(f"Calling Anthropic API with model: {settings.TIER3_MODEL}")
        logger.info(f"Prompt length: {len(prompt)} characters")
        
        response = client.messages.create(
            model=settings.TIER3_MODEL,
            max_tokens=3000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        logger.info(f"Received response from Anthropic API")
        logger.info(f"Response type: {type(response.content[0])}")
        
        content = response.content[0].text
        logger.info(f"Response content length: {len(content)} characters")
        logger.info(f"Response preview: {content[:200]}...")
        
        # Extract JSON
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
            logger.info("Extracted JSON from markdown code block")
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
            logger.info("Extracted content from generic code block")
        
        logger.info("Parsing JSON response...")
        parsed_result = json.loads(content)
        logger.info(f"Successfully parsed JSON with keys: {list(parsed_result.keys())}")
        
        return parsed_result
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing failed: {e}")
        logger.error(f"Content that failed to parse: {content[:500]}")
        return {
            "executive_summary": f"Synthesis generation failed: JSON parsing error - {str(e)}",
            "key_insights": [],
            "questions_for_user": [],
            "memory_proposals": [],
            "action_recommendations": []
        }
    except Exception as e:
        logger.error(f"Synthesis generation failed: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            "executive_summary": f"Synthesis generation failed: {str(e)}",
            "key_insights": [],
            "questions_for_user": [],
            "memory_proposals": [],
            "action_recommendations": []
        }


async def run_synthesis():
    """
    Run Tier 3 synthesis.
    Generates executive summary, insights, and recommendations using Claude Sonnet 4.5.
    """
    logger.info("Starting synthesis...")
    start_time = datetime.utcnow()
    
    # Gather data
    observations = get_recent_observations(limit=100)
    patterns = get_recent_patterns(limit=30)
    canonical_memory = get_canonical_memory()
    previous_synthesis = get_latest_synthesis()
    
    if not observations and not patterns:
        logger.info("No data available for synthesis")
        return {"status": "skipped", "reason": "no_data"}
    
    logger.info(f"Synthesizing {len(observations)} observations and {len(patterns)} patterns")
    
    # Initialize Anthropic client
    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    
    # Generate synthesis
    synthesis_result = generate_synthesis(
        client,
        observations,
        patterns,
        canonical_memory,
        previous_synthesis
    )
    
    # FIX #2: Mark observations as processed (Tier 3)
    if observations:
        from db.neon import mark_observations_processed_tier3
        observation_ids = [str(obs['id']) for obs in observations]
        mark_observations_processed_tier3(observation_ids)
        logger.info(f"Marked {len(observation_ids)} observations as processed (Tier 3)")
    
    # Store synthesis
    synthesis_number = get_next_synthesis_number()
    
    synthesis_data = {
        'synthesis_type': 'daily',
        'synthesis_number': synthesis_number,
        'executive_summary': synthesis_result['executive_summary'],
        'key_insights': json.dumps(synthesis_result['key_insights']),
        'questions_for_bradley': json.dumps(synthesis_result['questions_for_user']),
        'suggested_memory_updates': json.dumps(synthesis_result['memory_proposals']),
        'action_recommendations': json.dumps(synthesis_result['action_recommendations']),
        'observations_count': len(observations),
        'patterns_count': len(patterns),
        'created_at': datetime.utcnow()
    }
    
    try:
        logger.info(f"Attempting to store synthesis #{synthesis_number}")
        logger.info(f"Synthesis data keys: {list(synthesis_data.keys())}")
        logger.info(f"Executive summary length: {len(synthesis_data['executive_summary'])} chars")
        
        synthesis_id = store_synthesis(synthesis_data)
        
        logger.info(f"✅ Successfully stored synthesis #{synthesis_number} with ID {synthesis_id}")
        logger.info(f"Synthesis contains {len(synthesis_result['key_insights'])} insights, {len(synthesis_result['questions_for_user'])} questions, {len(synthesis_result['memory_proposals'])} memory proposals")
    except Exception as e:
        logger.error(f"❌ Failed to store synthesis: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {"status": "error", "error": str(e)}
    
    duration = (datetime.utcnow() - start_time).total_seconds()
    logger.info(f"Synthesis complete in {duration:.1f}s")
    
    return {
        "status": "success",
        "synthesis_number": synthesis_number,
        "observations_processed": len(observations),
        "patterns_processed": len(patterns),
        "insights_count": len(synthesis_result['key_insights']),
        "questions_count": len(synthesis_result['questions_for_user']),
        "duration_seconds": duration
    }
