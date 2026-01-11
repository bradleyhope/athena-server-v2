"""
Athena Server v2 - Evolution Engine
Weekly job that analyzes patterns, feedback, and performance to propose system improvements.
This is the core of Athena's autonomous learning capability.
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from decimal import Decimal

from anthropic import Anthropic

from config import settings
from db.neon import db_cursor
from db.brain import (
    get_brain_status,
    get_core_identity,
    get_boundaries,
    get_values,
    get_workflows,
    get_evolution_proposals,
    log_evolution,
    record_performance_metric,
)

logger = logging.getLogger("athena.jobs.evolution")


def get_recent_feedback(days: int = 7) -> List[Dict]:
    """Get feedback from the last N days."""
    with db_cursor() as cursor:
        cursor.execute("""
            SELECT * FROM feedback_history
            WHERE created_at > NOW() - INTERVAL '%s days'
            ORDER BY created_at DESC
        """, (days,))
        return cursor.fetchall()


def get_recent_patterns(days: int = 7) -> List[Dict]:
    """Get patterns from the last N days."""
    with db_cursor() as cursor:
        cursor.execute("""
            SELECT * FROM patterns
            WHERE detected_at > NOW() - INTERVAL '%s days'
            ORDER BY confidence DESC
            LIMIT 50
        """, (days,))
        return cursor.fetchall()


def get_recent_synthesis(days: int = 7) -> List[Dict]:
    """Get synthesis records from the last N days."""
    with db_cursor() as cursor:
        cursor.execute("""
            SELECT * FROM synthesis_memory
            WHERE created_at > NOW() - INTERVAL '%s days'
            ORDER BY created_at DESC
            LIMIT 20
        """, (days,))
        return cursor.fetchall()


def get_workflow_performance() -> List[Dict]:
    """Get workflow usage and success metrics."""
    workflows = get_workflows()
    
    performance = []
    for w in workflows:
        performance.append({
            'workflow_name': w['workflow_name'],
            'times_used': w.get('times_used', 0),
            'success_rate': float(w.get('success_rate', 1.0)),
            'last_used': str(w.get('last_used', 'never')),
            'enabled': w['enabled']
        })
    
    return performance


def analyze_feedback_patterns(feedback: List[Dict]) -> Dict:
    """Analyze feedback to identify improvement areas."""
    if not feedback:
        return {'total': 0, 'patterns': []}
    
    # Count feedback types
    positive = sum(1 for f in feedback if f.get('sentiment') == 'positive')
    negative = sum(1 for f in feedback if f.get('sentiment') == 'negative')
    neutral = len(feedback) - positive - negative
    
    # Group by category
    categories = {}
    for f in feedback:
        cat = f.get('category', 'general')
        if cat not in categories:
            categories[cat] = {'positive': 0, 'negative': 0, 'neutral': 0}
        
        sentiment = f.get('sentiment', 'neutral')
        categories[cat][sentiment] = categories[cat].get(sentiment, 0) + 1
    
    return {
        'total': len(feedback),
        'positive': positive,
        'negative': negative,
        'neutral': neutral,
        'by_category': categories
    }


def generate_evolution_proposals(
    client: Anthropic,
    identity: Dict,
    boundaries: List[Dict],
    values: List[Dict],
    workflows: List[Dict],
    feedback_analysis: Dict,
    patterns: List[Dict],
    synthesis_records: List[Dict]
) -> List[Dict]:
    """
    Use Claude to analyze the system and propose evolutions.
    """
    # Prepare context
    identity_summary = {k: v.get('value') for k, v in identity.items()}
    boundaries_summary = [{'type': b['boundary_type'], 'rule': b['rule']} for b in boundaries]
    values_summary = [{'name': v['value_name'], 'priority': v['priority']} for v in values]
    workflows_summary = [{'name': w['workflow_name'], 'enabled': w['enabled'], 'success_rate': w.get('success_rate', 1.0)} for w in workflows]
    
    patterns_summary = [
        {'type': p['pattern_type'], 'description': p['description'][:100], 'confidence': float(p['confidence']) if p['confidence'] else 0.0}
        for p in patterns[:20]
    ]
    
    # Extract key insights from synthesis
    synthesis_insights = []
    for s in synthesis_records[:5]:
        try:
            insights = json.loads(s.get('key_insights', '[]'))
            synthesis_insights.extend(insights[:3])
        except:
            pass
    
    prompt = f"""You are analyzing Athena's brain to propose system evolutions.

## CURRENT IDENTITY
{json.dumps(identity_summary, indent=2)}

## CURRENT BOUNDARIES ({len(boundaries)} total)
{json.dumps(boundaries_summary, indent=2)}

## CURRENT VALUES ({len(values)} total)
{json.dumps(values_summary, indent=2)}

## CURRENT WORKFLOWS ({len(workflows)} total)
{json.dumps(workflows_summary, indent=2)}

## FEEDBACK ANALYSIS (last 7 days)
{json.dumps(feedback_analysis, indent=2)}

## RECENT PATTERNS (top 20 by confidence)
{json.dumps(patterns_summary, indent=2)}

## RECENT SYNTHESIS INSIGHTS
{json.dumps(synthesis_insights, indent=2)}

Based on this analysis, propose 1-5 system evolutions. Each evolution should:
1. Be specific and actionable
2. Have clear justification based on the data
3. Include a confidence score (0.0-1.0)
4. Specify the category (identity, boundary, value, workflow, preference)

Consider:
- Are there patterns suggesting new workflows?
- Is there feedback suggesting boundary adjustments?
- Are there values that should be reprioritized?
- Are there workflows with low success rates that need improvement?
- Are there new preferences that should be learned?

Respond in JSON format:
{{
    "analysis_summary": "Brief summary of what you observed",
    "proposals": [
        {{
            "evolution_type": "workflow_learned|preference_learned|boundary_adjusted|value_reprioritized|identity_refined",
            "category": "identity|boundary|value|workflow|preference",
            "description": "What to change",
            "change_data": {{}},  // Specific data for the change
            "justification": "Why this change is proposed",
            "confidence": 0.8
        }}
    ]
}}

If no evolutions are warranted, return an empty proposals array with an explanation in analysis_summary.
"""

    try:
        response = client.messages.create(
            model=settings.TIER3_MODEL,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        content = response.content[0].text
        
        # Extract JSON
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        
        result = json.loads(content)
        return result.get('proposals', [])
        
    except Exception as e:
        logger.error(f"Evolution proposal generation failed: {e}")
        return []


async def run_evolution_engine():
    """
    Run the weekly evolution engine.
    Analyzes patterns, feedback, and performance to propose system improvements.
    """
    logger.info("Starting evolution engine...")
    start_time = datetime.utcnow()
    
    # Check if evolution is enabled
    status = get_brain_status()
    if status and not status.get('config', {}).get('evolution_enabled', True):
        logger.info("Evolution engine is disabled, skipping")
        return {"status": "skipped", "reason": "disabled"}
    
    # Gather data
    identity = get_core_identity()
    boundaries = get_boundaries()
    values = get_values()
    workflows = get_workflows()
    
    feedback = get_recent_feedback(days=7)
    patterns = get_recent_patterns(days=7)
    synthesis_records = get_recent_synthesis(days=7)
    
    feedback_analysis = analyze_feedback_patterns(feedback)
    
    logger.info(f"Evolution data: {len(feedback)} feedback, {len(patterns)} patterns, {len(synthesis_records)} synthesis")
    
    # Initialize Anthropic client
    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    
    # Generate proposals
    proposals = generate_evolution_proposals(
        client,
        identity,
        boundaries,
        values,
        workflows,
        feedback_analysis,
        patterns,
        synthesis_records
    )
    
    # Store proposals
    stored_count = 0
    for proposal in proposals:
        try:
            evolution_id = log_evolution(
                evolution_type=proposal.get('evolution_type', 'unknown'),
                category=proposal.get('category', 'general'),
                description=proposal.get('description', ''),
                change_data=proposal.get('change_data', {}),
                source='evolution_engine',
                confidence=proposal.get('confidence', 0.5)
            )
            logger.info(f"Stored evolution proposal: {evolution_id}")
            stored_count += 1
        except Exception as e:
            logger.error(f"Failed to store evolution proposal: {e}")
    
    # Record performance metric
    duration = (datetime.utcnow() - start_time).total_seconds()
    try:
        record_performance_metric(
            metric_name='evolution_engine_run',
            metric_value=stored_count,
            metric_unit='proposals',
            context={
                'feedback_count': len(feedback),
                'patterns_count': len(patterns),
                'duration_seconds': duration
            }
        )
    except Exception as e:
        logger.warning(f"Failed to record performance metric: {e}")
    
    logger.info(f"Evolution engine complete: {stored_count} proposals in {duration:.1f}s")
    
    return {
        "status": "success",
        "proposals_generated": stored_count,
        "feedback_analyzed": len(feedback),
        "patterns_analyzed": len(patterns),
        "duration_seconds": duration
    }


# Manual run function for testing
def manual_run():
    """Run evolution engine manually for testing."""
    import asyncio
    asyncio.run(run_evolution_engine())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    manual_run()
